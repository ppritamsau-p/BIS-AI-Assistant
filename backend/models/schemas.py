"""Pydantic contracts shared by the API layer and the AI layer."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

Language = Literal["en", "hi", "bn"]
Confidence = Literal["high", "medium", "low"]


# --------------------------------------------------------------------------
# Evidence / sources
# --------------------------------------------------------------------------
class SourceRef(BaseModel):
    """A pointer back into the indexed BIS corpus. Never synthesised by the LLM."""

    standard_number: str | None = None
    title: str | None = None
    document_type: str = "Indian Standard"
    clause: str | None = None
    section: str | None = None
    page: int | None = None
    source: str = "BIS"
    source_url: str | None = None
    chunk_id: str | None = None
    excerpt: str | None = None
    score: float = 0.0


class EvidenceChunk(BaseModel):
    chunk_id: str
    standard_number: str | None = None
    title: str | None = None
    content: str
    page: int | None = None
    section: str | None = None
    clause: str | None = None
    document_type: str = "Indian Standard"
    source_url: str | None = None
    score: float = 0.0
    lexical_score: float = 0.0
    semantic_score: float = 0.0

    def to_source(self) -> SourceRef:
        return SourceRef(
            standard_number=self.standard_number,
            title=self.title,
            document_type=self.document_type,
            clause=self.clause,
            section=self.section,
            page=self.page,
            source_url=self.source_url,
            chunk_id=self.chunk_id,
            excerpt=self.content[:320],
            score=round(self.score, 4),
        )


# --------------------------------------------------------------------------
# Knowledge-base records
# --------------------------------------------------------------------------
class Standard(BaseModel):
    id: str
    standard_number: str
    title: str
    scope: str = ""
    category: str = ""
    industry: str = ""
    edition: str = ""
    publication_date: str = ""
    status: str = "Active"
    keywords: list[str] = Field(default_factory=list)
    materials: list[str] = Field(default_factory=list)
    intended_use: list[str] = Field(default_factory=list)
    related_standards: list[str] = Field(default_factory=list)
    certification_required: bool | None = None
    certification_scheme: str | None = None
    testing_summary: str = ""
    source_url: str | None = None
    summary_hi: str | None = None
    summary_bn: str | None = None
    demo: bool = True


class StandardMatch(BaseModel):
    standard: Standard
    relevance: float
    reasons: list[str] = Field(default_factory=list)
    match_factors: dict[str, bool] = Field(default_factory=dict)
    sources: list[SourceRef] = Field(default_factory=list)


class CertificationScheme(BaseModel):
    id: str
    scheme_name: str
    short_name: str = ""
    product_category: str = ""
    applies_to: list[str] = Field(default_factory=list)
    standard_numbers: list[str] = Field(default_factory=list)
    mandatory: bool = False
    requirements: list[str] = Field(default_factory=list)
    documents: list[str] = Field(default_factory=list)
    procedure: list[str] = Field(default_factory=list)
    testing: list[str] = Field(default_factory=list)
    inspection: str = ""
    typical_timeline: str = ""
    source_url: str | None = None
    demo: bool = True


class Laboratory(BaseModel):
    id: str
    name: str
    city: str = ""
    state: str = ""
    lab_type: str = ""
    recognition_status: str = ""
    recognition_scope: list[str] = Field(default_factory=list)
    testing_capabilities: list[str] = Field(default_factory=list)
    product_categories: list[str] = Field(default_factory=list)
    standards_covered: list[str] = Field(default_factory=list)
    contact: str = ""
    email: str = ""
    source_url: str | None = None
    demo: bool = True


class HallmarkingTopic(BaseModel):
    id: str
    topic: str
    category: str
    summary: str
    details: list[str] = Field(default_factory=list)
    source_url: str | None = None
    demo: bool = True


# --------------------------------------------------------------------------
# Product understanding
# --------------------------------------------------------------------------
class ProductUnderstanding(BaseModel):
    product: str = ""
    category: str = ""
    materials: list[str] = Field(default_factory=list)
    intended_use: str = ""
    industry: str = ""
    target_user: str = ""
    characteristics: list[str] = Field(default_factory=list)
    notes: str = ""


# --------------------------------------------------------------------------
# Structured assistant answer
# --------------------------------------------------------------------------
class CertificationInfo(BaseModel):
    required: str = "Not verified"
    scheme: str | None = None
    process: list[str] = Field(default_factory=list)
    documents: list[str] = Field(default_factory=list)
    inspection: str | None = None
    verified: bool = False


class TestingInfo(BaseModel):
    tests: list[str] = Field(default_factory=list)
    laboratory_category: str | None = None
    laboratories: list[Laboratory] = Field(default_factory=list)
    verified: bool = False


class AssistantAnswer(BaseModel):
    answer: str
    intent: str = "general"
    language: Language = "en"
    product_understanding: ProductUnderstanding | None = None
    standards: list[StandardMatch] = Field(default_factory=list)
    why_match: list[str] = Field(default_factory=list)
    certification: CertificationInfo | None = None
    testing: TestingInfo | None = None
    documents: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    sources: list[SourceRef] = Field(default_factory=list)
    confidence: Confidence = "low"
    confidence_score: float = 0.0
    evidence_found: bool = True
    generator: str = "extractive"
    guardrail_notes: list[str] = Field(default_factory=list)
    disclaimer: str = (
        "AI-generated guidance based on the indexed knowledge base. Verify against the complete "
        "product specification and the current official BIS requirements before acting."
    )


# --------------------------------------------------------------------------
# Requests / responses
# --------------------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None
    language: Language = "en"
    history: list[dict[str, str]] = Field(default_factory=list)


class StandardSearchRequest(BaseModel):
    query: str = ""
    status: str | None = None
    industry: str | None = None
    category: str | None = None
    year_from: int | None = None
    year_to: int | None = None
    limit: int = 20


class RecommendRequest(BaseModel):
    description: str
    language: Language = "en"
    limit: int = 5


class CertificationRequest(BaseModel):
    product: str | None = None
    standard_number: str | None = None
    language: Language = "en"


class LabSearchRequest(BaseModel):
    query: str = ""
    product_category: str | None = None
    standard_number: str | None = None
    test_type: str | None = None
    state: str | None = None
    city: str | None = None
    limit: int = 20


class HallmarkingRequest(BaseModel):
    query: str
    language: Language = "en"


class ComplianceRequest(BaseModel):
    product: str
    standard_number: str | None = None
    language: Language = "en"


class ComplianceItem(BaseModel):
    id: str
    label: str
    detail: str = ""
    completed: bool = False
    source: SourceRef | None = None


class ComplianceChecklist(BaseModel):
    product: str
    standard_number: str | None = None
    items: list[ComplianceItem]
    completed: int = 0
    total: int = 0
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    sources: list[SourceRef] = Field(default_factory=list)


class TranslateRequest(BaseModel):
    text: str
    target_language: Language = "hi"
    source_language: Language | None = None


class CompareRequest(BaseModel):
    standard_numbers: list[str]


class CompareRow(BaseModel):
    parameter: str
    values: dict[str, str]


class CompareResponse(BaseModel):
    standards: list[Standard]
    rows: list[CompareRow]
    sources: list[SourceRef] = Field(default_factory=list)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str


class HealthResponse(BaseModel):
    status: str
    version: str
    llm_enabled: bool
    llm_model: str | None
    storage: str
    embedding_provider: str
    demo_mode: bool
    indexed_chunks: int
    standards: int


class IngestResult(BaseModel):
    document_id: str
    filename: str
    standard_number: str | None
    pages: int
    chunks: int
    status: str
    message: str = ""
    extra: dict[str, Any] = Field(default_factory=dict)
