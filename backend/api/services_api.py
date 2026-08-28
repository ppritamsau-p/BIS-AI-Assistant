"""BIS service endpoints: certification, laboratories, hallmarking, compliance, translation."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.ai.composer import answer_question
from backend.ai.llm import LLMUnavailable, get_llm
from backend.api.deps import kb_dependency
from backend.database.store import KnowledgeBase
from backend.models.schemas import (
    AssistantAnswer,
    CertificationRequest,
    CertificationScheme,
    ComplianceChecklist,
    ComplianceRequest,
    HallmarkingRequest,
    HallmarkingTopic,
    LabSearchRequest,
    Laboratory,
    TranslateRequest,
)
from backend.services.compliance import generate_checklist

router = APIRouter(prefix="/api", tags=["bis-services"])


# --------------------------------------------------------------------------
# Certification
# --------------------------------------------------------------------------
@router.post("/certification/analyze", response_model=AssistantAnswer)
def analyze_certification(
    payload: CertificationRequest, kb: KnowledgeBase = Depends(kb_dependency)
) -> AssistantAnswer:
    question = payload.product or ""
    if payload.standard_number:
        question = f"{question} certification requirements for {payload.standard_number}".strip()
    if not question:
        raise HTTPException(400, "Provide a product description or a standard number")
    return answer_question(kb, question, language=payload.language, forced_intent="certification")


@router.get("/certification/schemes", response_model=list[CertificationScheme])
def list_schemes(kb: KnowledgeBase = Depends(kb_dependency)) -> list[CertificationScheme]:
    return kb.schemes


# --------------------------------------------------------------------------
# Laboratories
# --------------------------------------------------------------------------
@router.post("/labs/search", response_model=list[Laboratory])
def search_labs(payload: LabSearchRequest, kb: KnowledgeBase = Depends(kb_dependency)) -> list[Laboratory]:
    return kb.search_labs(
        query=payload.query,
        product_category=payload.product_category,
        standard_number=payload.standard_number,
        test_type=payload.test_type,
        state=payload.state,
        city=payload.city,
        limit=payload.limit,
    )


@router.get("/labs/facets")
def lab_facets(kb: KnowledgeBase = Depends(kb_dependency)) -> dict[str, list[str]]:
    labs = kb.laboratories
    return {
        "states": sorted({lab.state for lab in labs if lab.state}),
        "cities": sorted({lab.city for lab in labs if lab.city}),
        "categories": sorted({c for lab in labs for c in lab.product_categories}),
        "test_types": sorted({t for lab in labs for t in lab.testing_capabilities}),
        "standards": sorted({s for lab in labs for s in lab.standards_covered}),
    }


# --------------------------------------------------------------------------
# Hallmarking
# --------------------------------------------------------------------------
@router.post("/hallmarking/query", response_model=AssistantAnswer)
def hallmarking_query(
    payload: HallmarkingRequest, kb: KnowledgeBase = Depends(kb_dependency)
) -> AssistantAnswer:
    return answer_question(kb, payload.query, language=payload.language, forced_intent="hallmarking")


@router.get("/hallmarking/topics", response_model=list[HallmarkingTopic])
def hallmarking_topics(q: str = "", kb: KnowledgeBase = Depends(kb_dependency)) -> list[HallmarkingTopic]:
    return kb.hallmarking_topics(q)


# --------------------------------------------------------------------------
# Consumer
# --------------------------------------------------------------------------
@router.post("/consumer/query", response_model=AssistantAnswer)
def consumer_query(
    payload: HallmarkingRequest, kb: KnowledgeBase = Depends(kb_dependency)
) -> AssistantAnswer:
    return answer_question(kb, payload.query, language=payload.language, forced_intent="consumer")


# --------------------------------------------------------------------------
# Compliance
# --------------------------------------------------------------------------
@router.post("/compliance/generate", response_model=ComplianceChecklist)
def compliance(payload: ComplianceRequest, kb: KnowledgeBase = Depends(kb_dependency)) -> ComplianceChecklist:
    return generate_checklist(kb, payload.product, payload.standard_number, payload.language)


# --------------------------------------------------------------------------
# Translation
# --------------------------------------------------------------------------
@router.post("/translate")
def translate(payload: TranslateRequest) -> dict[str, object]:
    """Translate assistant output.

    Returns `translated: false` with the original text when no model is configured, rather
    than returning a machine-mangled approximation of regulatory guidance.
    """
    llm = get_llm()
    if not llm.available:
        return {
            "text": payload.text,
            "target_language": payload.target_language,
            "translated": False,
            "reason": (
                "Translation needs a configured language model. Set ANTHROPIC_API_KEY on the "
                "backend to enable it. The original text is returned unchanged."
            ),
        }
    try:
        return {
            "text": llm.translate(payload.text, payload.target_language),
            "target_language": payload.target_language,
            "translated": True,
        }
    except LLMUnavailable as exc:
        return {
            "text": payload.text,
            "target_language": payload.target_language,
            "translated": False,
            "reason": str(exc),
        }
