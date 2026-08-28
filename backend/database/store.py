"""In-process knowledge base.

Holds the structured BIS records and the chunk index, and rebuilds the retriever whenever
documents are added or removed. This is the default storage driver so the prototype runs
with no external services; `backend/database/pg.py` mirrors the same surface on
PostgreSQL + pgvector when DATABASE_URL is configured.

Everything served from here is tagged with its provenance. Nothing in this module ever
generates BIS content -- it only loads, indexes and returns what was ingested.
"""
from __future__ import annotations

import json
import threading
import uuid
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from backend.config import DATA_DIR, settings
from backend.models.schemas import (
    CertificationScheme,
    HallmarkingTopic,
    Laboratory,
    Standard,
)
from backend.rag.embeddings import build_embedder
from backend.rag.ingest import build_chunk_records, extract_document
from backend.retrieval.hybrid import HybridRetriever, IndexedChunk
from backend.retrieval.text import normalise_standard_number, tokenize

DOC_TYPE_BY_FOLDER = {
    "standards": "Indian Standard",
    "certification": "BIS Certification Guideline",
    "hallmarking": "BIS Hallmarking Guideline",
    "laboratories": "BIS Laboratory Information",
    "consumer": "BIS Consumer Guideline",
    "uploads": "Uploaded Document",
}


class KnowledgeBase:
    """Single source of truth for standards, schemes, labs and indexed chunks."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.standards: dict[str, Standard] = {}
        self.schemes: list[CertificationScheme] = []
        self.laboratories: list[Laboratory] = []
        self.hallmarking: list[HallmarkingTopic] = []

        self.chunks: list[IndexedChunk] = []
        self.documents: dict[str, dict[str, Any]] = {}
        self.failed_documents: list[dict[str, Any]] = []
        self.query_log: deque[dict[str, Any]] = deque(maxlen=500)

        self.retriever = HybridRetriever()
        self.embedder = build_embedder()
        self.last_updated: datetime | None = None
        self.storage_driver = "memory-json"

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------
    def load(self) -> None:
        with self._lock:
            self._load_structured()
            self.chunks = []
            self.documents = {}
            self.failed_documents = []
            self._index_structured_records()
            self._index_corpus_files()
            self._rebuild()

    def _read_json(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            self.failed_documents.append(
                {"filename": path.name, "reason": f"invalid JSON: {exc}", "at": _now()}
            )
            return {}

    def _load_structured(self) -> None:
        std_payload = self._read_json(DATA_DIR / "standards" / "standards.json")
        self.standards = {}
        for row in std_payload.get("standards", []):
            std = Standard(**row)
            self.standards[std.standard_number.upper()] = std

        scheme_payload = self._read_json(DATA_DIR / "certification" / "schemes.json")
        self.schemes = [CertificationScheme(**row) for row in scheme_payload.get("schemes", [])]

        lab_payload = self._read_json(DATA_DIR / "laboratories" / "laboratories.json")
        self.laboratories = [Laboratory(**row) for row in lab_payload.get("laboratories", [])]

        hm_payload = self._read_json(DATA_DIR / "hallmarking" / "topics.json")
        self.hallmarking = [HallmarkingTopic(**row) for row in hm_payload.get("topics", [])]

    def _index_structured_records(self) -> None:
        """Make the structured records retrievable as evidence in their own right.

        Without this, a query like "which standard covers stainless steel lunch boxes"
        could only match narrative document text, and would miss standards whose scope is
        recorded in the catalogue but whose full text has not been ingested.
        """
        for std in self.standards.values():
            body = (
                f"{std.standard_number} {std.title}\n"
                f"Scope: {std.scope}\n"
                f"Category: {std.category}. Industry: {std.industry}.\n"
                f"Materials: {', '.join(std.materials)}.\n"
                f"Intended use: {', '.join(std.intended_use)}.\n"
                f"Keywords: {', '.join(std.keywords)}.\n"
                f"Status: {std.status}. Edition: {std.edition} ({std.publication_date}).\n"
                f"Testing: {std.testing_summary}"
            )
            self.chunks.append(
                IndexedChunk(
                    chunk_id=f"catalogue:{std.id}",
                    content=body,
                    standard_number=std.standard_number,
                    title=std.title,
                    section="Catalogue record",
                    document_type="Indian Standard (catalogue record)",
                    source_url=std.source_url,
                    extra={"record": "standard", "record_id": std.id},
                )
            )

        for scheme in self.schemes:
            body = (
                f"{scheme.scheme_name}\n"
                f"Applies to: {', '.join(scheme.applies_to)}.\n"
                f"Mandatory: {'yes' if scheme.mandatory else 'not by default'}.\n"
                f"Requirements: {'; '.join(scheme.requirements)}\n"
                f"Documents: {'; '.join(scheme.documents)}\n"
                f"Procedure: {'; '.join(scheme.procedure)}\n"
                f"Testing: {'; '.join(scheme.testing)}\n"
                f"Inspection: {scheme.inspection}"
            )
            self.chunks.append(
                IndexedChunk(
                    chunk_id=f"catalogue:{scheme.id}",
                    content=body,
                    title=scheme.scheme_name,
                    section="Certification scheme",
                    document_type="BIS Certification Scheme",
                    source_url=scheme.source_url,
                    extra={"record": "scheme", "record_id": scheme.id},
                )
            )

        for topic in self.hallmarking:
            body = f"{topic.topic}\n{topic.summary}\n" + "\n".join(topic.details)
            self.chunks.append(
                IndexedChunk(
                    chunk_id=f"catalogue:{topic.id}",
                    content=body,
                    title=topic.topic,
                    section=topic.category,
                    document_type="BIS Hallmarking Information",
                    source_url=topic.source_url,
                    extra={"record": "hallmarking", "record_id": topic.id},
                )
            )

    def _index_corpus_files(self) -> None:
        for path in sorted(DATA_DIR.rglob("*")):
            if path.suffix.lower() not in {".txt", ".md", ".pdf"} or not path.is_file():
                continue
            folder = path.parent.name
            self._ingest_path(path, document_type=DOC_TYPE_BY_FOLDER.get(folder, "BIS Document"))

    def _ingest_path(self, path: Path, *, document_type: str) -> dict[str, Any] | None:
        try:
            doc = extract_document(path)
        except Exception as exc:
            self.failed_documents.append({"filename": path.name, "reason": str(exc), "at": _now()})
            return None

        std_number = doc.standard_number
        catalogue = self.standards.get((std_number or "").upper()) if std_number else None
        document_id = uuid.uuid4().hex[:12]

        records = build_chunk_records(
            doc,
            standard_number=std_number,
            title=(catalogue.title if catalogue else doc.title) or path.stem,
            document_type=document_type,
            source_url=(catalogue.source_url if catalogue else "https://www.bis.gov.in/"),
            document_id=document_id,
        )
        for rec in records:
            self.chunks.append(
                IndexedChunk(
                    chunk_id=rec["chunk_id"],
                    content=rec["content"],
                    standard_number=rec["standard_number"],
                    title=rec["title"],
                    page=rec["page"],
                    section=rec["section"],
                    clause=rec["clause"],
                    document_type=rec["document_type"],
                    source_url=rec["source_url"],
                    extra={"document_id": document_id},
                )
            )

        entry = {
            "document_id": document_id,
            "filename": path.name,
            "path": str(path),
            "standard_number": std_number,
            "title": records[0]["title"] if records else path.stem,
            "document_type": document_type,
            "pages": doc.pages,
            "chunks": len(records),
            "ocr_pages": doc.ocr_pages,
            "warnings": doc.warnings,
            "indexed_at": _now(),
        }
        self.documents[document_id] = entry
        for warning in doc.warnings:
            self.failed_documents.append(
                {"filename": path.name, "reason": warning, "at": _now(), "partial": True}
            )
        return entry

    def _rebuild(self) -> None:
        corpus = [c.searchable_text() for c in self.chunks]
        if hasattr(self.embedder, "fit"):
            self.embedder.fit(corpus)
        self.retriever.build(self.chunks, self.embedder)
        self.last_updated = datetime.now(timezone.utc)

    # ------------------------------------------------------------------
    # Admin operations
    # ------------------------------------------------------------------
    def add_document(self, path: Path, *, document_type: str = "Uploaded Document") -> dict[str, Any]:
        with self._lock:
            entry = self._ingest_path(Path(path), document_type=document_type)
            if entry is None:
                failure = self.failed_documents[-1] if self.failed_documents else {}
                raise RuntimeError(failure.get("reason", "ingestion failed"))
            self._rebuild()
            return entry

    def remove_document(self, document_id: str) -> bool:
        with self._lock:
            if document_id not in self.documents:
                return False
            self.chunks = [c for c in self.chunks if c.extra.get("document_id") != document_id]
            self.documents.pop(document_id, None)
            self._rebuild()
            return True

    def log_query(self, entry: dict[str, Any]) -> None:
        entry.setdefault("at", _now())
        self.query_log.appendleft(entry)

    # ------------------------------------------------------------------
    # Lookups
    # ------------------------------------------------------------------
    def get_standard(self, number: str) -> Standard | None:
        if not number:
            return None
        key = normalise_standard_number(number).upper()
        if key in self.standards:
            return self.standards[key]
        # Tolerate "IS 302" when the catalogue holds "IS 302-1".
        for std_key, std in self.standards.items():
            if std_key.split("-")[0] == key:
                return std
        return None

    def search_standards(
        self,
        query: str = "",
        *,
        status: str | None = None,
        industry: str | None = None,
        category: str | None = None,
        year_from: int | None = None,
        year_to: int | None = None,
        limit: int = 20,
    ) -> list[Standard]:
        results = list(self.standards.values())

        if status:
            results = [s for s in results if s.status.lower() == status.lower()]
        if industry:
            results = [s for s in results if industry.lower() in s.industry.lower()]
        if category:
            results = [s for s in results if category.lower() in s.category.lower()]
        if year_from or year_to:
            def in_range(s: Standard) -> bool:
                try:
                    year = int(str(s.publication_date)[:4])
                except (TypeError, ValueError):
                    return False
                return (not year_from or year >= year_from) and (not year_to or year <= year_to)

            results = [s for s in results if in_range(s)]

        if query.strip():
            # Literal query terms decide *whether* a standard qualifies; synonyms only
            # adjust the ordering. Letting a synonym alone qualify a result meant that
            # "steel utensil" -- whose expansion includes "metal" -- surfaced gold
            # jewellery standards, because their category reads "Precious metal".
            literal = set(tokenize(query))
            expanded = set(tokenize(query, expand=True)) - literal
            scored: list[tuple[float, Standard]] = []

            for std in results:
                haystack = " ".join(
                    [std.standard_number, std.title, std.scope, std.category, std.industry]
                    + std.keywords + std.materials + std.intended_use
                )
                tokens = set(tokenize(haystack))
                if not tokens:
                    continue

                exact_number = normalise_standard_number(query).upper() == std.standard_number.upper()
                literal_hits = len(literal & tokens)
                if literal_hits == 0 and not exact_number:
                    continue

                score = literal_hits / (len(literal) or 1)
                score += 0.35 * len(expanded & tokens) / (len(expanded) or 1)
                if exact_number:
                    score += 5.0
                scored.append((score, std))

            scored.sort(key=lambda kv: kv[0], reverse=True)
            results = [s for _, s in scored]

        return results[:limit]

    def schemes_for(
        self, *, category: str | None = None, standard_number: str | None = None
    ) -> list[CertificationScheme]:
        matches: list[CertificationScheme] = []
        std_key = normalise_standard_number(standard_number).upper() if standard_number else None
        for scheme in self.schemes:
            hit = False
            if std_key and any(s.upper() == std_key for s in scheme.standard_numbers):
                hit = True
            if category and any(category.lower() == a.lower() for a in scheme.applies_to):
                hit = True
            if hit:
                matches.append(scheme)
        return matches

    def search_labs(
        self,
        *,
        query: str = "",
        product_category: str | None = None,
        standard_number: str | None = None,
        test_type: str | None = None,
        state: str | None = None,
        city: str | None = None,
        limit: int = 20,
    ) -> list[Laboratory]:
        std_key = normalise_standard_number(standard_number).upper() if standard_number else None
        results: list[Laboratory] = []
        for lab in self.laboratories:
            if state and state.lower() not in lab.state.lower():
                continue
            if city and city.lower() not in lab.city.lower():
                continue
            if product_category and not any(
                product_category.lower() in c.lower() for c in lab.product_categories
            ):
                continue
            if std_key and not any(s.upper() == std_key for s in lab.standards_covered):
                continue
            if test_type and not any(
                test_type.lower() in cap.lower() for cap in lab.testing_capabilities
            ):
                continue
            if query.strip():
                haystack = " ".join(
                    [lab.name, lab.lab_type, lab.state, lab.city]
                    + lab.testing_capabilities + lab.product_categories + lab.standards_covered
                )
                if not (set(tokenize(query, expand=True)) & set(tokenize(haystack))):
                    continue
            results.append(lab)
        return results[:limit]

    def labs_for_standard(self, standard_number: str | None, limit: int = 3) -> list[Laboratory]:
        if not standard_number:
            return []
        return self.search_labs(standard_number=standard_number, limit=limit)

    def hallmarking_topics(self, query: str = "") -> list[HallmarkingTopic]:
        if not query.strip():
            return list(self.hallmarking)
        q = set(tokenize(query, expand=True))
        scored = []
        for topic in self.hallmarking:
            tokens = set(tokenize(f"{topic.topic} {topic.category} {topic.summary} " + " ".join(topic.details)))
            overlap = len(q & tokens)
            if overlap:
                scored.append((overlap, topic))
        scored.sort(key=lambda kv: kv[0], reverse=True)
        return [t for _, t in scored]

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------
    def stats(self) -> dict[str, Any]:
        by_type: dict[str, int] = {}
        for chunk in self.chunks:
            by_type[chunk.document_type] = by_type.get(chunk.document_type, 0) + 1
        return {
            "standards": len(self.standards),
            "indexed_chunks": len(self.chunks),
            "documents": len(self.documents),
            "certification_schemes": len(self.schemes),
            "laboratories": len(self.laboratories),
            "hallmarking_topics": len(self.hallmarking),
            "failed_documents": len(self.failed_documents),
            "chunks_by_type": by_type,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "storage_driver": self.storage_driver,
            "embedding_provider": getattr(self.embedder, "name", "unknown"),
            "demo_mode": settings.demo_mode,
        }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


_kb: KnowledgeBase | None = None


def get_kb() -> KnowledgeBase:
    global _kb  # noqa: PLW0603 - single process-wide index
    if _kb is None:
        kb = KnowledgeBase()
        kb.load()
        if settings.use_postgres:
            try:
                from backend.database.pg import attach_postgres  # noqa: PLC0415

                attach_postgres(kb)
            except Exception as exc:  # pragma: no cover - database dependent
                print(f"[store] PostgreSQL unavailable ({exc}); continuing with in-memory index")
        _kb = kb
    return _kb


def reset_kb() -> None:
    """Drop the cached knowledge base (used by the admin re-index endpoint and tests)."""
    global _kb  # noqa: PLW0603
    _kb = None
