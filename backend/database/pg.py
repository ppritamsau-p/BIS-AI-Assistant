"""PostgreSQL + pgvector storage driver.

Activated by setting DATABASE_URL. It mirrors the in-memory knowledge base into
PostgreSQL and then swaps the retriever's vector index for one that runs the ANN search
in the database, so the same retrieval code path serves both deployments.

Kept deliberately additive: if anything here fails the assistant keeps working off the
in-memory index rather than going down.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from backend.config import settings
from backend.retrieval.vector import PgVectorIndex

if TYPE_CHECKING:  # pragma: no cover
    from backend.database.store import KnowledgeBase

SCHEMA = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS standards (
    id               TEXT PRIMARY KEY,
    standard_number  TEXT NOT NULL UNIQUE,
    title            TEXT NOT NULL,
    scope            TEXT,
    category         TEXT,
    industry         TEXT,
    edition          TEXT,
    publication_date TEXT,
    status           TEXT,
    keywords         TEXT[],
    materials        TEXT[],
    intended_use     TEXT[],
    related_standards TEXT[],
    certification_required BOOLEAN,
    certification_scheme   TEXT,
    testing_summary  TEXT,
    source_url       TEXT,
    is_demo          BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS standard_chunks (
    id             BIGSERIAL PRIMARY KEY,
    chunk_key      TEXT NOT NULL UNIQUE,
    document_id    TEXT,
    standard_id    TEXT REFERENCES standards(id) ON DELETE CASCADE,
    standard_number TEXT,
    title          TEXT,
    content        TEXT NOT NULL,
    page_number    INTEGER,
    section        TEXT,
    clause         TEXT,
    document_type  TEXT,
    source_url     TEXT,
    embedding      vector(%(dim)s)
);

CREATE INDEX IF NOT EXISTS standard_chunks_number_idx ON standard_chunks (standard_number);
CREATE INDEX IF NOT EXISTS standard_chunks_fts_idx
    ON standard_chunks USING GIN (to_tsvector('english', content));
CREATE INDEX IF NOT EXISTS standard_chunks_embedding_idx
    ON standard_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE TABLE IF NOT EXISTS certification_schemes (
    id              TEXT PRIMARY KEY,
    scheme_name     TEXT NOT NULL,
    product_category TEXT,
    standard_numbers TEXT[],
    mandatory       BOOLEAN DEFAULT FALSE,
    requirements    JSONB,
    documents       JSONB,
    procedure       JSONB,
    testing         JSONB,
    inspection      TEXT,
    source_url      TEXT,
    is_demo         BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS laboratories (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    city          TEXT,
    state         TEXT,
    lab_type      TEXT,
    recognition_status TEXT,
    recognized_scope   TEXT[],
    testing_capabilities TEXT[],
    product_categories   TEXT[],
    standards_covered    TEXT[],
    contact       TEXT,
    email         TEXT,
    source_url    TEXT,
    is_demo       BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS conversations (
    id         TEXT PRIMARY KEY,
    user_id    TEXT,
    title      TEXT,
    language   TEXT DEFAULT 'en',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS messages (
    id              BIGSERIAL PRIMARY KEY,
    conversation_id TEXT REFERENCES conversations(id) ON DELETE CASCADE,
    role            TEXT NOT NULL,
    content         TEXT NOT NULL,
    payload         JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS query_logs (
    id         BIGSERIAL PRIMARY KEY,
    query      TEXT,
    intent     TEXT,
    confidence TEXT,
    top_score  REAL,
    evidence_count INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
"""


def _engine():
    from sqlalchemy import create_engine  # noqa: PLC0415

    return create_engine(settings.database_url, pool_pre_ping=True, future=True)


def attach_postgres(kb: "KnowledgeBase") -> None:
    """Create the schema, sync the in-memory records into it, and switch the vector index."""
    from sqlalchemy import text as sql_text  # noqa: PLC0415
    from sqlalchemy.orm import sessionmaker  # noqa: PLC0415

    engine = _engine()
    session_factory = sessionmaker(bind=engine, future=True)

    dim = getattr(kb.embedder, "dim", settings.embedding_dim)
    with engine.begin() as conn:
        for statement in (SCHEMA % {"dim": dim}).split(";\n"):
            if statement.strip():
                conn.execute(sql_text(statement))

    _sync(kb, session_factory)

    kb.retriever.vectors = PgVectorIndex(session_factory)
    # Keep an in-memory copy as the fallback path inside PgVectorIndex.
    texts = [c.searchable_text() for c in kb.chunks]
    vectors = kb.embedder.embed_documents(texts)
    kb.retriever.vectors.add_many([c.chunk_id for c in kb.chunks], vectors)
    kb.storage_driver = "postgresql+pgvector"


def _sync(kb: "KnowledgeBase", session_factory) -> None:  # noqa: ANN001
    from sqlalchemy import text as sql_text  # noqa: PLC0415

    texts = [c.searchable_text() for c in kb.chunks]
    vectors = kb.embedder.embed_documents(texts)

    with session_factory() as session:
        for std in kb.standards.values():
            session.execute(
                sql_text(
                    """
                    INSERT INTO standards (id, standard_number, title, scope, category, industry,
                        edition, publication_date, status, keywords, materials, intended_use,
                        related_standards, certification_required, certification_scheme,
                        testing_summary, source_url, is_demo)
                    VALUES (:id, :num, :title, :scope, :cat, :ind, :ed, :pub, :status, :kw, :mat,
                            :use, :rel, :certreq, :scheme, :testing, :url, :demo)
                    ON CONFLICT (id) DO UPDATE SET
                        title = EXCLUDED.title, scope = EXCLUDED.scope, status = EXCLUDED.status
                    """
                ),
                {
                    "id": std.id, "num": std.standard_number, "title": std.title,
                    "scope": std.scope, "cat": std.category, "ind": std.industry,
                    "ed": std.edition, "pub": std.publication_date, "status": std.status,
                    "kw": std.keywords, "mat": std.materials, "use": std.intended_use,
                    "rel": std.related_standards, "certreq": std.certification_required,
                    "scheme": std.certification_scheme, "testing": std.testing_summary,
                    "url": std.source_url, "demo": std.demo,
                },
            )

        for lab in kb.laboratories:
            session.execute(
                sql_text(
                    """
                    INSERT INTO laboratories (id, name, city, state, lab_type, recognition_status,
                        recognized_scope, testing_capabilities, product_categories,
                        standards_covered, contact, email, source_url, is_demo)
                    VALUES (:id, :name, :city, :state, :type, :status, :scope, :caps, :cats,
                            :stds, :contact, :email, :url, :demo)
                    ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name
                    """
                ),
                {
                    "id": lab.id, "name": lab.name, "city": lab.city, "state": lab.state,
                    "type": lab.lab_type, "status": lab.recognition_status,
                    "scope": lab.recognition_scope, "caps": lab.testing_capabilities,
                    "cats": lab.product_categories, "stds": lab.standards_covered,
                    "contact": lab.contact, "email": lab.email, "url": lab.source_url,
                    "demo": lab.demo,
                },
            )

        session.execute(sql_text("DELETE FROM standard_chunks"))
        for chunk, vector in zip(kb.chunks, vectors):
            std = kb.standards.get((chunk.standard_number or "").upper())
            session.execute(
                sql_text(
                    """
                    INSERT INTO standard_chunks (chunk_key, document_id, standard_id,
                        standard_number, title, content, page_number, section, clause,
                        document_type, source_url, embedding)
                    VALUES (:key, :doc, :std_id, :num, :title, :content, :page, :section,
                            :clause, :dtype, :url, CAST(:emb AS vector))
                    ON CONFLICT (chunk_key) DO NOTHING
                    """
                ),
                {
                    "key": chunk.chunk_id,
                    "doc": chunk.extra.get("document_id"),
                    "std_id": std.id if std else None,
                    "num": chunk.standard_number, "title": chunk.title,
                    "content": chunk.content, "page": chunk.page,
                    "section": chunk.section, "clause": chunk.clause,
                    "dtype": chunk.document_type, "url": chunk.source_url,
                    "emb": "[" + ",".join(f"{v:.6f}" for v in vector) + "]",
                },
            )
        session.commit()
