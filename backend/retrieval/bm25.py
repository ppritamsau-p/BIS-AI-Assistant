"""Okapi BM25 over the indexed chunks.

Implemented in-process rather than pulled in as a dependency: the corpus is small, the
maths is short, and it keeps the prototype installable with nothing but FastAPI.
When PostgreSQL is configured the same role is played by `tsvector` ranking, but the
fusion layer above treats both identically.
"""
from __future__ import annotations

import math
from collections import Counter, defaultdict

from backend.retrieval.text import tokenize

K1 = 1.5
B = 0.75


class BM25Index:
    def __init__(self, k1: float = K1, b: float = B) -> None:
        self.k1 = k1
        self.b = b
        self.doc_ids: list[str] = []
        self.doc_len: list[int] = []
        self.term_freqs: list[Counter[str]] = []
        self.postings: dict[str, list[int]] = defaultdict(list)
        self.avg_len: float = 0.0
        self._idf: dict[str, float] = {}

    # -- build -------------------------------------------------------------
    def add(self, doc_id: str, text: str) -> None:
        tokens = tokenize(text)
        idx = len(self.doc_ids)
        self.doc_ids.append(doc_id)
        self.doc_len.append(len(tokens))
        tf = Counter(tokens)
        self.term_freqs.append(tf)
        for term in tf:
            self.postings[term].append(idx)

    def finalize(self) -> None:
        n = len(self.doc_ids)
        self.avg_len = (sum(self.doc_len) / n) if n else 0.0
        self._idf = {}
        for term, docs in self.postings.items():
            df = len(docs)
            # BM25+ style floor keeps very common terms from going negative.
            self._idf[term] = max(math.log(1 + (n - df + 0.5) / (df + 0.5)), 0.01)

    # -- query -------------------------------------------------------------
    def search(self, query: str, limit: int = 40) -> list[tuple[str, float]]:
        if not self.doc_ids:
            return []
        q_tokens = tokenize(query, expand=True)
        if not q_tokens:
            return []

        scores: dict[int, float] = defaultdict(float)
        q_counts = Counter(q_tokens)
        for term, q_tf in q_counts.items():
            idf = self._idf.get(term)
            if idf is None:
                continue
            # Repeated query terms count, but with diminishing weight.
            q_weight = 1.0 + math.log(q_tf)
            for idx in self.postings[term]:
                tf = self.term_freqs[idx][term]
                dl = self.doc_len[idx] or 1
                denom = tf + self.k1 * (1 - self.b + self.b * dl / (self.avg_len or 1))
                scores[idx] += q_weight * idf * (tf * (self.k1 + 1)) / denom

        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:limit]
        if not ranked:
            return []
        top = ranked[0][1] or 1.0
        return [(self.doc_ids[i], s / top) for i, s in ranked]

    def __len__(self) -> int:
        return len(self.doc_ids)
