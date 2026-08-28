"""Dense vector index.

The in-memory implementation is a brute-force cosine scan, which is the right choice for
a corpus of this size (thousands of chunks) and keeps the prototype dependency-free.
`PgVectorIndex` swaps in the same interface backed by `pgvector`'s ANN operators once a
DATABASE_URL is configured.
"""
from __future__ import annotations

from backend.rag.embeddings import cosine


class VectorIndex:
    """Brute-force cosine index over L2-normalised vectors."""

    def __init__(self) -> None:
        self.doc_ids: list[str] = []
        self.vectors: list[list[float]] = []

    def add(self, doc_id: str, vector: list[float]) -> None:
        self.doc_ids.append(doc_id)
        self.vectors.append(vector)

    def add_many(self, doc_ids: list[str], vectors: list[list[float]]) -> None:
        self.doc_ids.extend(doc_ids)
        self.vectors.extend(vectors)

    def search(self, query_vector: list[float], limit: int = 40) -> list[tuple[str, float]]:
        if not self.vectors or not query_vector:
            return []
        scored = [
            (self.doc_ids[i], cosine(query_vector, vec)) for i, vec in enumerate(self.vectors)
        ]
        scored = [(doc_id, s) for doc_id, s in scored if s > 0]
        scored.sort(key=lambda kv: kv[1], reverse=True)
        return scored[:limit]

    def clear(self) -> None:
        self.doc_ids.clear()
        self.vectors.clear()

    def __len__(self) -> int:
        return len(self.doc_ids)


class PgVectorIndex(VectorIndex):
    """pgvector-backed search over ``standard_chunks.embedding``.

    Falls back to the in-memory parent implementation if the query fails, so a database
    hiccup degrades retrieval quality instead of breaking the assistant.
    """

    def __init__(self, session_factory) -> None:  # noqa: ANN001 - sqlalchemy sessionmaker
        super().__init__()
        self._session_factory = session_factory

    def search(self, query_vector: list[float], limit: int = 40) -> list[tuple[str, float]]:
        from sqlalchemy import text as sql_text  # noqa: PLC0415

        literal = "[" + ",".join(f"{v:.6f}" for v in query_vector) + "]"
        stmt = sql_text(
            """
            SELECT chunk_key, 1 - (embedding <=> CAST(:qv AS vector)) AS score
            FROM standard_chunks
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> CAST(:qv AS vector)
            LIMIT :lim
            """
        )
        try:
            with self._session_factory() as session:
                rows = session.execute(stmt, {"qv": literal, "lim": limit}).fetchall()
            return [(row[0], float(row[1])) for row in rows]
        except Exception as exc:  # pragma: no cover - database dependent
            print(f"[vector] pgvector search failed ({exc}); using in-memory index")
            return super().search(query_vector, limit)
