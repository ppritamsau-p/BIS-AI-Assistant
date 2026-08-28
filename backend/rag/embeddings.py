"""Embedding providers.

Two implementations behind one interface:

``LocalHashingEmbedder`` (default)
    Deterministic, offline, dependency-free. It computes IDF over the indexed corpus and
    projects IDF-weighted word tokens plus character 4-grams into a fixed-width dense
    vector via signed feature hashing. The result is a genuine dense vector that stores in
    pgvector and behaves sensibly under cosine similarity -- but it is a *demo-grade*
    stand-in, not a trained sentence encoder. Swap the provider before production.

``SentenceTransformerEmbedder``
    Used when ``EMBEDDING_PROVIDER=sbert`` and ``sentence-transformers`` is installed.

Both satisfy the same protocol, so the retrieval layer never knows which is active.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Iterable, Protocol, runtime_checkable

from backend.config import settings
from backend.retrieval.text import tokenize


@runtime_checkable
class EmbeddingProvider(Protocol):
    name: str
    dim: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


def _l2_normalise(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vec))
    if norm <= 1e-12:
        return vec
    return [v / norm for v in vec]


def cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity for vectors that are already L2-normalised."""
    if not a or not b:
        return 0.0
    return sum(x * y for x, y in zip(a, b))


class LocalHashingEmbedder:
    """IDF-weighted signed feature hashing. Deterministic and network-free."""

    name = "local-hashing-tfidf"

    def __init__(self, dim: int | None = None) -> None:
        self.dim = dim or settings.embedding_dim
        self.idf: dict[str, float] = {}
        self.doc_count = 0

    # -- vocabulary --------------------------------------------------------
    def fit(self, corpus: Iterable[str]) -> "LocalHashingEmbedder":
        df: Counter[str] = Counter()
        n = 0
        for text in corpus:
            n += 1
            df.update(set(tokenize(text)))
        self.doc_count = n
        self.idf = {
            term: math.log((n + 1) / (count + 1)) + 1.0 for term, count in df.items()
        }
        return self

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"dim": self.dim, "doc_count": self.doc_count, "idf": self.idf}),
            encoding="utf-8",
        )

    def load(self, path: Path) -> bool:
        if not path.exists():
            return False
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.dim = payload.get("dim", self.dim)
        self.doc_count = payload.get("doc_count", 0)
        self.idf = payload.get("idf", {})
        return True

    # -- hashing -----------------------------------------------------------
    def _slot(self, feature: str) -> tuple[int, float]:
        digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
        value = int.from_bytes(digest, "big")
        return value % self.dim, 1.0 if (value >> 63) & 1 else -1.0

    def _vector(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        tokens = tokenize(text)
        if not tokens:
            return vec

        counts = Counter(tokens)
        max_tf = max(counts.values())
        for term, tf in counts.items():
            # Sub-linear TF keeps long clauses from dominating.
            weight = (0.5 + 0.5 * tf / max_tf) * self.idf.get(term, 1.0)
            idx, sign = self._slot(term)
            vec[idx] += sign * weight

        # Character 4-grams give partial credit for morphological variants that the
        # stemmer misses ("hallmarked" vs "hallmarking").
        joined = " ".join(tokens)
        for i in range(len(joined) - 3):
            gram = joined[i : i + 4]
            if " " in gram:
                continue
            idx, sign = self._slot("#" + gram)
            vec[idx] += sign * 0.15

        return _l2_normalise(vec)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)


class SentenceTransformerEmbedder:
    """Real sentence encoder, used when the optional dependency is available."""

    name = "sentence-transformers"

    def __init__(self, model_name: str | None = None) -> None:
        from sentence_transformers import SentenceTransformer  # noqa: PLC0415

        self.model_name = model_name or settings.embedding_model
        self._model = SentenceTransformer(self.model_name)
        self.dim = int(self._model.get_sentence_embedding_dimension())

    def fit(self, corpus: Iterable[str]) -> "SentenceTransformerEmbedder":  # no-op
        return self

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors = self._model.encode(texts, normalize_embeddings=True)
        return [list(map(float, v)) for v in vectors]

    def embed_query(self, text: str) -> list[float]:
        return list(map(float, self._model.encode(text, normalize_embeddings=True)))


def build_embedder() -> EmbeddingProvider:
    """Factory honouring EMBEDDING_PROVIDER, falling back to the offline embedder."""
    provider = (settings.embedding_provider or "local").lower()
    if provider in {"sbert", "sentence-transformers", "st"}:
        try:
            return SentenceTransformerEmbedder()
        except Exception as exc:  # pragma: no cover - optional dependency
            print(f"[embeddings] sentence-transformers unavailable ({exc}); using local embedder")
    return LocalHashingEmbedder()
