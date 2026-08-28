"""Hybrid retrieval: BM25 + dense vectors, fused, then reranked.

Why both halves are mandatory here (spec section 18):

* A user typing ``IS 15111`` needs an exact designation hit. Dense vectors blur exact
  identifiers, so the lexical half carries that case.
* A user typing "steel lunch box for school children" never uses the vocabulary of the
  standard's scope clause. The dense half carries that case.

Fusion is Reciprocal Rank Fusion, which combines two rankings without needing the two
score distributions to be comparable. The reranker then applies domain signals that
neither retriever can see: exact designation mentions, title hits, and clause structure.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from backend.config import settings
from backend.models.schemas import EvidenceChunk
from backend.retrieval.bm25 import BM25Index
from backend.retrieval.text import extract_standard_numbers, tokenize
from backend.retrieval.vector import VectorIndex

RRF_K = 60  # standard RRF damping constant


@dataclass
class IndexedChunk:
    """A chunk as held in the index, with the metadata every answer must cite."""

    chunk_id: str
    content: str
    standard_number: str | None = None
    title: str | None = None
    page: int | None = None
    section: str | None = None
    clause: str | None = None
    document_type: str = "Indian Standard"
    source_url: str | None = None
    extra: dict = field(default_factory=dict)

    def searchable_text(self) -> str:
        head = " ".join(x for x in [self.standard_number, self.title, self.section, self.clause] if x)
        return f"{head}\n{self.content}"


class HybridRetriever:
    def __init__(self, vector_index: VectorIndex | None = None) -> None:
        self.chunks: dict[str, IndexedChunk] = {}
        self.bm25 = BM25Index()
        self.vectors = vector_index or VectorIndex()
        self.embedder = None  # injected by the knowledge base on build
        self._built = False

    # -- build -------------------------------------------------------------
    def build(self, chunks: list[IndexedChunk], embedder) -> None:  # noqa: ANN001
        self.chunks = {c.chunk_id: c for c in chunks}
        self.embedder = embedder

        self.bm25 = BM25Index()
        for chunk in chunks:
            self.bm25.add(chunk.chunk_id, chunk.searchable_text())
        self.bm25.finalize()

        if not isinstance(self.vectors, VectorIndex) or type(self.vectors) is VectorIndex:
            self.vectors.clear()
            texts = [c.searchable_text() for c in chunks]
            vectors = embedder.embed_documents(texts)
            self.vectors.add_many([c.chunk_id for c in chunks], vectors)

        self._built = True

    # -- query -------------------------------------------------------------
    def retrieve(
        self,
        query: str,
        *,
        limit: int | None = None,
        candidates: int | None = None,
        standard_filter: str | None = None,
    ) -> list[EvidenceChunk]:
        if not self._built or not self.chunks:
            return []

        limit = limit or settings.retrieval_top_k
        candidates = candidates or settings.retrieval_candidates

        lexical = dict(self.bm25.search(query, limit=candidates))
        semantic: dict[str, float] = {}
        if self.embedder is not None:
            qv = self.embedder.embed_query(query)
            semantic = dict(self.vectors.search(qv, limit=candidates))

        lex_rank = {cid: r for r, cid in enumerate(sorted(lexical, key=lexical.get, reverse=True))}
        sem_rank = {cid: r for r, cid in enumerate(sorted(semantic, key=semantic.get, reverse=True))}

        fused: dict[str, float] = {}
        for cid in set(lex_rank) | set(sem_rank):
            score = 0.0
            if cid in lex_rank:
                score += 1.0 / (RRF_K + lex_rank[cid] + 1)
            if cid in sem_rank:
                score += 1.0 / (RRF_K + sem_rank[cid] + 1)
            fused[cid] = score

        reranked = self._rerank(query, fused, lexical, semantic, standard_filter)
        return reranked[:limit]

    # -- admissibility -----------------------------------------------------
    @staticmethod
    def _admissible(
        *, designation_match: bool, lexical_score: float, semantic_score: float, coverage: float
    ) -> bool:
        """Is this chunk real evidence, or just the least-bad row in an empty result set?

        RRF fusion is rank-based: the top result of a hopeless query scores exactly as high
        as the top result of a perfect one. Asking "how do I bake a cake" therefore returns
        BIS clauses at score ~1.0 unless absolute relevance is checked separately. This
        gate is what lets the assistant say "I could not verify this" instead of confidently
        answering a question the corpus knows nothing about.
        """
        if designation_match:
            return True
        if lexical_score >= settings.min_lexical_score and coverage > 0:
            return True
        return semantic_score >= settings.min_semantic_score

    # -- rerank ------------------------------------------------------------
    def _rerank(
        self,
        query: str,
        fused: dict[str, float],
        lexical: dict[str, float],
        semantic: dict[str, float],
        standard_filter: str | None,
    ) -> list[EvidenceChunk]:
        q_tokens = set(tokenize(query, expand=True))
        q_standards = set(extract_standard_numbers(query))
        # "IS 302" in the query must still match a chunk tagged "IS 302-1": the user rarely
        # types the part number, and parts of a standard are the same document family.
        q_bases = {n.split("-")[0] for n in q_standards}
        results: list[EvidenceChunk] = []

        # Normalise fused scores into 0..1 so downstream confidence maths is stable.
        max_fused = max(fused.values(), default=1.0) or 1.0

        for cid, base in fused.items():
            chunk = self.chunks.get(cid)
            if chunk is None:
                continue
            if standard_filter and (chunk.standard_number or "").upper() != standard_filter.upper():
                continue

            score = base / max_fused

            # Exact designation match is the single strongest signal available.
            chunk_number = (chunk.standard_number or "").upper()
            designation_match = bool(q_standards) and bool(chunk_number) and (
                chunk_number in q_standards or chunk_number.split("-")[0] in q_bases
            )
            if designation_match:
                score += 0.55

            # Title overlap: the query talks about what this standard is called.
            title_tokens = set(tokenize(chunk.title or ""))
            if title_tokens:
                overlap = len(q_tokens & title_tokens) / len(title_tokens)
                score += 0.25 * overlap

            # Body overlap, capped so long chunks cannot win on length alone.
            body_tokens = set(tokenize(chunk.content))
            coverage = 0.0
            if body_tokens and q_tokens:
                coverage = len(q_tokens & body_tokens) / len(q_tokens)
                score += 0.20 * min(coverage, 1.0)

            # Prefer chunks that carry a precise citation anchor.
            if chunk.clause:
                score += 0.04
            if chunk.page:
                score += 0.02

            if not self._admissible(
                designation_match=designation_match,
                lexical_score=lexical.get(cid, 0.0),
                semantic_score=semantic.get(cid, 0.0),
                coverage=coverage,
            ):
                continue

            results.append(
                EvidenceChunk(
                    chunk_id=chunk.chunk_id,
                    standard_number=chunk.standard_number,
                    title=chunk.title,
                    content=chunk.content,
                    page=chunk.page,
                    section=chunk.section,
                    clause=chunk.clause,
                    document_type=chunk.document_type,
                    source_url=chunk.source_url,
                    score=round(score, 5),
                    lexical_score=round(lexical.get(cid, 0.0), 5),
                    semantic_score=round(semantic.get(cid, 0.0), 5),
                )
            )

        results.sort(key=lambda c: c.score, reverse=True)
        return results

    def __len__(self) -> int:
        return len(self.chunks)
