"""Tests for the parts of the pipeline where a regression would be invisible.

The emphasis is deliberate: a broken button is obvious, but a retriever that quietly
starts answering off-topic questions, or a guardrail that stops stripping unsupported
citations, looks exactly like a working system from the outside. Those are what is tested
here.

    pip install pytest && python -m pytest backend/tests -q
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.ai import guardrails
from backend.ai.composer import answer_question
from backend.ai.confidence import score_evidence
from backend.ai.intent import detect_intent, understand_product
from backend.database.store import get_kb
from backend.main import app
from backend.models.schemas import AssistantAnswer, EvidenceChunk, Standard, StandardMatch
from backend.rag.chunker import chunk_document
from backend.retrieval.text import extract_standard_numbers, normalise_standard_number


@pytest.fixture(scope="module")
def kb():
    return get_kb()


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


# --------------------------------------------------------------------------
# Designation parsing
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("IS 302-1 : 2008", ["IS 302-1"]),
        ("IS 15111:2002", ["IS 15111"]),          # 4 digits after the colon is a year
        ("IS 9873 Part 3", ["IS 9873-3"]),
        ("IS 1293-2019", ["IS 1293"]),            # year, not part 2019
        ("IS 694", ["IS 694"]),
        ("no standard here", []),
    ],
)
def test_designation_parsing(text, expected):
    assert extract_standard_numbers(text) == expected


def test_normalise_is_stable():
    assert normalise_standard_number("is 302-1 : 2008") == "IS 302-1"
    assert normalise_standard_number("IS 302-1") == normalise_standard_number("is  302 - 1")


# --------------------------------------------------------------------------
# Chunking
# --------------------------------------------------------------------------
def test_chunker_preserves_clause_and_page():
    text = (
        "<<<PAGE:1>>>\n1 SCOPE\nThis standard covers widgets of every description and is "
        "written at sufficient length that the chunker treats it as a real clause body.\n"
        "<<<PAGE:2>>>\n5.2 Thickness\nThe wall thickness shall not be less than the declared "
        "value, measured at three points and averaged across the sample."
    )
    chunks = chunk_document(text)
    clauses = {c.clause for c in chunks}

    assert "1" in clauses and "5.2" in clauses
    thickness = next(c for c in chunks if c.clause == "5.2")
    assert thickness.page == 2, "page markers must survive chunking or citations are wrong"
    assert "<<<PAGE" not in thickness.content, "page markers must be stripped from stored text"


# --------------------------------------------------------------------------
# Retrieval admissibility -- the anti-hallucination gate
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    "query",
    [
        "How do I bake a chocolate cake?",
        "what is the capital of France",
        "cricket world cup schedule",
        "write me a poem about the sea",
    ],
)
def test_off_topic_queries_retrieve_nothing(kb, query):
    """Rank-based fusion always produces a top result; only the absolute gate stops it."""
    assert kb.retriever.retrieve(query, limit=5) == []


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("I manufacture stainless steel lunch boxes for school children", "IS 14756"),
        ("Explain IS 302 in simple language", "IS 302-1"),
        ("PVC insulated cable for building wiring", "IS 694"),
        ("gold jewellery purity marking", "IS 1417"),
    ],
)
def test_on_topic_queries_retrieve_the_right_standard(kb, query, expected):
    found = {c.standard_number for c in kb.retriever.retrieve(query, limit=5)}
    assert expected in found, f"{query!r} should retrieve {expected}, got {found}"


def test_partial_designation_matches_the_part(kb):
    """A user typing 'IS 302' must reach 'IS 302-1'."""
    found = {c.standard_number for c in kb.retriever.retrieve("IS 302 requirements", limit=5)}
    assert "IS 302-1" in found


# --------------------------------------------------------------------------
# Intent
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("I manufacture lunch boxes. Which standards may apply?", "product_standard"),
        ("How can I obtain BIS certification for my product?", "certification"),
        ("Where can I test my electrical product?", "laboratory"),
        ("What is hallmarking?", "hallmarking"),
        ("Explain IS 302 in simple language", "standard_lookup"),
        ("Compare IS 14756 and IS 5522", "compare"),
    ],
)
def test_intent_routing(message, expected):
    assert detect_intent(message) == expected


def test_product_understanding_extracts_profile():
    product = understand_product(
        "I manufacture stainless steel lunch boxes for school children"
    )
    assert "stainless steel" in product.materials
    assert product.category == "Food-contact household product"
    assert product.target_user == "school children"
    assert "steel" not in product.materials, "the more specific material should win"


# --------------------------------------------------------------------------
# Guardrails
# --------------------------------------------------------------------------
def _chunk(**kwargs) -> EvidenceChunk:
    base = {"chunk_id": "c1", "content": "text", "score": 1.0}
    return EvidenceChunk(**{**base, **kwargs})


def _standard(number: str) -> Standard:
    return Standard(id=number, standard_number=number, title=f"{number} title")


def test_guardrail_strips_unsupported_citation():
    answer = AssistantAnswer(answer="This is covered by IS 99999 and IS 14756.")
    chunks = [_chunk(standard_number="IS 14756", content="IS 14756 covers utensils")]

    verified = guardrails.verify_answer(answer, chunks)

    assert "[unverified: IS 99999]" in verified.answer
    assert "IS 14756" in verified.answer
    assert any("IS 99999" in note for note in verified.guardrail_notes)


def test_guardrail_drops_unsupported_standard_card():
    answer = AssistantAnswer(
        answer="Answer text.",
        standards=[
            StandardMatch(standard=_standard("IS 14756"), relevance=0.9),
            StandardMatch(standard=_standard("IS 99999"), relevance=0.8),
        ],
    )
    chunks = [_chunk(standard_number="IS 14756", content="utensils")]

    verified = guardrails.verify_answer(answer, chunks)

    assert [m.standard.standard_number for m in verified.standards] == ["IS 14756"]


def test_guardrail_accepts_part_of_a_supported_standard():
    """Evidence tagged 'IS 302' supports a card for 'IS 302-1' -- same document family."""
    answer = AssistantAnswer(
        answer="See IS 302-1.",
        standards=[StandardMatch(standard=_standard("IS 302-1"), relevance=0.9)],
    )
    chunks = [_chunk(standard_number="IS 302", content="general requirements")]

    verified = guardrails.verify_answer(answer, chunks)

    assert len(verified.standards) == 1
    assert "unverified" not in verified.answer


def test_guardrail_softens_unsupported_legal_obligation():
    answer = AssistantAnswer(answer="Certification is mandatory for this product.")
    chunks = [_chunk(content="This standard covers dimensions and finish.")]

    verified = guardrails.verify_answer(answer, chunks)

    assert "is mandatory" not in verified.answer
    assert "not established" in verified.answer


def test_guardrail_keeps_obligation_when_evidence_supports_it():
    answer = AssistantAnswer(answer="Certification is mandatory for this product.")
    chunks = [_chunk(content="Products notified under a Quality Control Order are mandatory.")]

    assert "is mandatory" in guardrails.verify_answer(answer, chunks).answer


def test_no_evidence_forces_a_refusal():
    answer = AssistantAnswer(answer="Some confident claim.", standards=[])
    verified = guardrails.verify_answer(answer, [])

    assert verified.evidence_found is False
    assert verified.answer == guardrails.INSUFFICIENT_EVIDENCE_MESSAGE


# --------------------------------------------------------------------------
# Confidence
# --------------------------------------------------------------------------
def test_confidence_is_low_without_evidence():
    label, score, _ = score_evidence([])
    assert label == "low" and score == 0.0


def test_confidence_rises_with_corroboration():
    weak = [_chunk(chunk_id="a", score=0.3, standard_number="IS 1")]
    strong = [
        _chunk(chunk_id=f"c{i}", score=1.6, standard_number="IS 1", clause="5.2", page=3)
        for i in range(4)
    ]
    assert score_evidence(strong)[1] > score_evidence(weak)[1]


# --------------------------------------------------------------------------
# End-to-end answers
# --------------------------------------------------------------------------
def test_product_question_produces_grounded_answer(kb):
    answer = answer_question(
        kb, "I manufacture stainless steel lunch boxes for school children. Which standards apply?"
    )

    assert answer.evidence_found
    assert answer.intent == "product_standard"
    assert answer.product_understanding is not None
    assert "IS 14756" in [m.standard.standard_number for m in answer.standards]
    assert answer.sources, "a grounded answer must carry sources"
    assert any(s.clause or s.page for s in answer.sources), "at least one citable anchor"


def test_off_topic_question_is_refused(kb):
    answer = answer_question(kb, "How do I bake a chocolate cake?")

    assert answer.evidence_found is False
    assert answer.confidence == "low"
    assert answer.standards == []
    assert guardrails.INSUFFICIENT_EVIDENCE_MESSAGE in answer.answer


def test_process_question_does_not_invent_a_product_standard(kb):
    """A generic certification question must not present a random product standard."""
    answer = answer_question(kb, "What documents are required for certification?")
    assert answer.standards == []


# --------------------------------------------------------------------------
# API surface
# --------------------------------------------------------------------------
def test_health_and_meta(client):
    assert client.get("/api/health").status_code == 200
    meta = client.get("/api/meta").json()
    assert meta["standards"] > 0 and meta["indexed_chunks"] > 0


def test_admin_requires_authentication(client):
    assert client.get("/api/admin/stats").status_code == 401


def test_admin_rejects_a_non_admin_role(client):
    token = client.post(
        "/api/auth/login", json={"username": "user", "password": "user123"}
    ).json()["access_token"]

    response = client.get("/api/admin/stats", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_admin_accepts_an_admin_token(client):
    token = client.post(
        "/api/auth/login", json={"username": "admin", "password": "admin123"}
    ).json()["access_token"]

    response = client.get("/api/admin/stats", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


def test_tampered_token_is_rejected(client):
    token = client.post(
        "/api/auth/login", json={"username": "admin", "password": "admin123"}
    ).json()["access_token"]
    head, payload, _sig = token.split(".")
    forged = f"{head}.{payload}.AAAAAAAAAAAAAAAAAAAAAAAAAAAA"

    assert client.get(
        "/api/admin/stats", headers={"Authorization": f"Bearer {forged}"}
    ).status_code == 401


def test_compare_requires_two_standards(client):
    assert client.post("/api/standards/compare", json={"standard_numbers": ["IS 14756"]}).status_code == 400


def test_compare_marks_unknown_values_rather_than_inventing(client):
    rows = client.post(
        "/api/standards/compare", json={"standard_numbers": ["IS 14756", "IS 5522"]}
    ).json()["rows"]

    for row in rows:
        for value in row["values"].values():
            assert value.strip(), "a comparison cell must never be blank"


def test_chat_stream_emits_the_real_stages(client):
    response = client.post("/api/chat/stream", json={"message": "What is hallmarking?"})
    events = [line[7:] for line in response.text.split("\n") if line.startswith("event: ")]

    assert "retrieving" in events
    assert "verified" in events
    assert events[-1] == "done"


def test_labs_are_never_generated(client):
    """Laboratory results must come from the dataset, never from the model."""
    labs = client.post("/api/labs/search", json={"standard_number": "IS 302-1"}).json()
    assert all(lab["demo"] for lab in labs)
    assert all("DEMO" in lab["recognition_status"].upper() for lab in labs)
