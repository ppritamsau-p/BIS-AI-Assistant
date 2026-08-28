"""Standards catalogue: search, detail, recommendation and comparison."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.ai.composer import answer_question
from backend.api.deps import kb_dependency
from backend.database.store import KnowledgeBase
from backend.models.schemas import (
    AssistantAnswer,
    CompareRequest,
    CompareResponse,
    RecommendRequest,
    Standard,
    StandardSearchRequest,
)
from backend.services.compliance import compare_standards

router = APIRouter(prefix="/api/standards", tags=["standards"])


@router.post("/search", response_model=list[Standard])
def search(payload: StandardSearchRequest, kb: KnowledgeBase = Depends(kb_dependency)) -> list[Standard]:
    return kb.search_standards(
        payload.query,
        status=payload.status,
        industry=payload.industry,
        category=payload.category,
        year_from=payload.year_from,
        year_to=payload.year_to,
        limit=payload.limit,
    )


@router.get("/facets")
def facets(kb: KnowledgeBase = Depends(kb_dependency)) -> dict[str, list[str]]:
    """Filter options derived from the catalogue, so the UI never hardcodes them."""
    standards = kb.standards.values()
    return {
        "statuses": sorted({s.status for s in standards if s.status}),
        "industries": sorted({s.industry for s in standards if s.industry}),
        "categories": sorted({s.category for s in standards if s.category}),
        "years": sorted({str(s.publication_date)[:4] for s in standards if s.publication_date}, reverse=True),
    }


@router.post("/recommend", response_model=AssistantAnswer)
def recommend(payload: RecommendRequest, kb: KnowledgeBase = Depends(kb_dependency)) -> AssistantAnswer:
    """Product description -> ranked applicable standards with explainable factors."""
    return answer_question(
        kb,
        payload.description,
        language=payload.language,
        forced_intent="product_standard",
        limit=payload.limit,
    )


@router.post("/compare", response_model=CompareResponse)
def compare(payload: CompareRequest, kb: KnowledgeBase = Depends(kb_dependency)) -> CompareResponse:
    if len(payload.standard_numbers) < 2:
        raise HTTPException(400, "Select at least two standards to compare")
    return compare_standards(kb, payload.standard_numbers[:4])


@router.get("/{standard_number:path}", response_model=Standard)
def detail(standard_number: str, kb: KnowledgeBase = Depends(kb_dependency)) -> Standard:
    std = kb.get_standard(standard_number)
    if std is None:
        raise HTTPException(404, f"{standard_number} is not present in the indexed knowledge base")
    return std


@router.get("/{standard_number:path}/evidence")
def evidence(
    standard_number: str,
    limit: int = Query(8, ge=1, le=25),
    kb: KnowledgeBase = Depends(kb_dependency),
) -> dict:
    """The indexed passages behind a standard -- the 'View Source' target in the UI."""
    std = kb.get_standard(standard_number)
    if std is None:
        raise HTTPException(404, f"{standard_number} is not present in the indexed knowledge base")
    chunks = kb.retriever.retrieve(
        f"{std.standard_number} {std.title}", limit=limit, standard_filter=std.standard_number
    )
    return {
        "standard": std.model_dump(),
        "passages": [c.model_dump() for c in chunks],
        "demo": std.demo,
    }
