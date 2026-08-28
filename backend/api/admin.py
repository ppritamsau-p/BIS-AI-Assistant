"""Authentication and the admin knowledge-base console."""
from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from backend.api.deps import kb_dependency
from backend.config import settings
from backend.database.store import KnowledgeBase, reset_kb
from backend.models.schemas import IngestResult, LoginRequest, TokenResponse
from backend.services.auth import authenticate, create_token, require_admin

auth_router = APIRouter(prefix="/api/auth", tags=["auth"])
router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])

ALLOWED_SUFFIXES = {".pdf", ".txt", ".md"}
MAX_UPLOAD_BYTES = 40 * 1024 * 1024


@auth_router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    user = authenticate(payload.username, payload.password)
    if user is None:
        raise HTTPException(401, "Invalid username or password")
    return TokenResponse(
        access_token=create_token(user["username"], user["role"]),
        role=user["role"],
        username=user["username"],
    )


@auth_router.get("/me")
def me(user: dict = Depends(require_admin)) -> dict:
    return {"username": user.get("sub"), "role": user.get("role")}


# --------------------------------------------------------------------------
# Dashboard
# --------------------------------------------------------------------------
@router.get("/stats")
def stats(kb: KnowledgeBase = Depends(kb_dependency)) -> dict:
    payload = kb.stats()
    payload["llm_enabled"] = settings.llm_enabled
    payload["llm_model"] = settings.llm_model if settings.llm_enabled else None
    return payload


@router.get("/documents")
def documents(kb: KnowledgeBase = Depends(kb_dependency)) -> list[dict]:
    return sorted(kb.documents.values(), key=lambda d: d["indexed_at"], reverse=True)


@router.get("/documents/failed")
def failed_documents(kb: KnowledgeBase = Depends(kb_dependency)) -> list[dict]:
    return kb.failed_documents


@router.get("/queries")
def query_logs(kb: KnowledgeBase = Depends(kb_dependency)) -> list[dict]:
    return list(kb.query_log)


@router.get("/retrieval-quality")
def retrieval_quality(kb: KnowledgeBase = Depends(kb_dependency)) -> dict:
    """Aggregate confidence over recent queries -- the signal that the corpus needs work."""
    logs = list(kb.query_log)
    if not logs:
        return {"queries": 0, "message": "No queries recorded yet."}

    by_confidence = {"high": 0, "medium": 0, "low": 0}
    zero_evidence = 0
    total_score = 0.0
    for entry in logs:
        by_confidence[entry.get("confidence", "low")] = by_confidence.get(entry.get("confidence", "low"), 0) + 1
        if not entry.get("evidence_count"):
            zero_evidence += 1
        total_score += float(entry.get("top_score") or 0.0)

    return {
        "queries": len(logs),
        "by_confidence": by_confidence,
        "unanswered": zero_evidence,
        "average_top_score": round(total_score / len(logs), 4),
        "low_confidence_rate": round(by_confidence["low"] / len(logs), 3),
        "note": (
            "A rising low-confidence rate means the indexed corpus does not cover what users "
            "are asking about. Ingest the relevant BIS documents rather than loosening the "
            "evidence threshold."
        ),
    }


# --------------------------------------------------------------------------
# Knowledge-base management
# --------------------------------------------------------------------------
@router.post("/documents/upload", response_model=IngestResult)
def upload_document(
    file: UploadFile = File(...), kb: KnowledgeBase = Depends(kb_dependency)
) -> IngestResult:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(400, f"Unsupported file type '{suffix}'. Allowed: PDF, TXT, MD.")

    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    target = settings.upload_dir / Path(file.filename).name

    size = 0
    with target.open("wb") as out:
        while chunk := file.file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_UPLOAD_BYTES:
                out.close()
                target.unlink(missing_ok=True)
                raise HTTPException(413, "File exceeds the 40 MB upload limit")
            out.write(chunk)

    try:
        entry = kb.add_document(target, document_type="Uploaded Document")
    except RuntimeError as exc:
        target.unlink(missing_ok=True)
        raise HTTPException(422, f"Could not process the document: {exc}") from exc

    return IngestResult(
        document_id=entry["document_id"],
        filename=entry["filename"],
        standard_number=entry["standard_number"],
        pages=entry["pages"],
        chunks=entry["chunks"],
        status="indexed",
        message=(
            f"Indexed {entry['chunks']} chunks from {entry['pages']} page(s)."
            + (f" OCR was used on {len(entry['ocr_pages'])} page(s)." if entry["ocr_pages"] else "")
        ),
        extra={"warnings": entry["warnings"], "ocr_pages": entry["ocr_pages"]},
    )


@router.delete("/documents/{document_id}")
def delete_document(document_id: str, kb: KnowledgeBase = Depends(kb_dependency)) -> dict:
    if not kb.remove_document(document_id):
        raise HTTPException(404, "Document not found")
    return {"status": "removed", "document_id": document_id, "indexed_chunks": len(kb.chunks)}


@router.post("/reindex")
def reindex() -> dict:
    """Rebuild the whole index from data/ -- used after editing the source files."""
    reset_kb()
    from backend.database.store import get_kb  # noqa: PLC0415

    kb = get_kb()
    return {"status": "reindexed", **kb.stats()}


@router.delete("/uploads")
def clear_uploads() -> dict:
    """Remove every uploaded document and rebuild from the bundled corpus."""
    if settings.upload_dir.exists():
        shutil.rmtree(settings.upload_dir)
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    reset_kb()
    from backend.database.store import get_kb  # noqa: PLC0415

    return {"status": "cleared", **get_kb().stats()}
