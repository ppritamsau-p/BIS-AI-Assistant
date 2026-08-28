"""Post-generation verification.

The system prompt asks the model not to invent BIS content. This module checks whether it
did, because an instruction that is never verified is an assumption. Every standard
designation in the generated text is matched against the designations actually present in
the retrieved evidence; unsupported ones are struck through in the text and reported as
guardrail notes rather than silently deleted, so a reviewer can see what happened.

The same check runs over the extractive composer's output. It costs nothing there (that
path cannot invent designations by construction) but it means the invariant is enforced in
one place regardless of which generator produced the answer.
"""
from __future__ import annotations

import re

from backend.models.schemas import AssistantAnswer, EvidenceChunk
from backend.retrieval.text import extract_standard_numbers

INSUFFICIENT_EVIDENCE_MESSAGE = (
    "I could not verify this information from the available BIS knowledge sources."
)

# Phrases that would assert a legal obligation. Allowed only when the evidence discusses
# mandatory status, otherwise softened -- this is the single most consequential thing the
# assistant could get wrong.
OBLIGATION_RE = re.compile(
    r"\b(is mandatory|are mandatory|is compulsory|you must obtain|legally required|"
    r"required by law|is required by the government)\b",
    re.IGNORECASE,
)
MANDATORY_EVIDENCE_RE = re.compile(
    r"\b(mandatory|compulsory|quality control order|qco|compulsory registration)\b", re.IGNORECASE
)


def evidence_standards(chunks: list[EvidenceChunk]) -> set[str]:
    """Designations that legitimately appear in the retrieved evidence.

    Both the full designation and its base number are recorded, so that evidence written
    as "IS 302" still supports a card for "IS 302-1". Parts of one standard are the same
    document family; treating them as unrelated would strip correct citations.
    """
    found: set[str] = set()

    def record(value: str) -> None:
        value = value.upper().strip()
        if value:
            found.add(value)
            found.add(value.split("-")[0].strip())

    for chunk in chunks:
        if chunk.standard_number:
            record(chunk.standard_number)
        for num in extract_standard_numbers(f"{chunk.title or ''} {chunk.content}"):
            record(num)
    return found


def _supported(number: str, allowed: set[str]) -> bool:
    number = number.upper().strip()
    return number in allowed or number.split("-")[0].strip() in allowed


def verify_answer(answer: AssistantAnswer, chunks: list[EvidenceChunk]) -> AssistantAnswer:
    """Strip unsupported claims and record what was stripped."""
    allowed = evidence_standards(chunks)
    notes: list[str] = list(answer.guardrail_notes)

    # 1. Designations cited in the narrative must exist in the evidence.
    cited = set(extract_standard_numbers(answer.answer))
    unsupported = {c for c in cited if not _supported(c, allowed)}
    if unsupported:
        for num in sorted(unsupported):
            answer.answer = re.sub(
                re.escape(num) + r"(?:\s*[:\-]\s*(?:19|20)\d{2})?",
                f"[unverified: {num}]",
                answer.answer,
            )
            notes.append(
                f"Removed citation of {num}: it does not appear in the retrieved evidence."
            )

    # 2. Standard cards must correspond to retrieved evidence.
    kept = []
    for match in answer.standards:
        if _supported(match.standard.standard_number, allowed):
            kept.append(match)
        else:
            notes.append(
                f"Dropped recommended standard {match.standard.standard_number}: "
                "not supported by retrieved evidence."
            )
    answer.standards = kept

    # 3. Do not assert a legal obligation the evidence does not establish.
    evidence_text = " ".join(c.content for c in chunks)
    if OBLIGATION_RE.search(answer.answer) and not MANDATORY_EVIDENCE_RE.search(evidence_text):
        answer.answer = OBLIGATION_RE.sub("may be required (not established from the evidence)", answer.answer)
        notes.append(
            "Softened a statement of legal obligation: the retrieved evidence does not "
            "establish mandatory status for this product."
        )
        if answer.certification:
            answer.certification.required = "Not established from evidence"
            answer.certification.verified = False

    # 4. No evidence means no technical answer.
    if not chunks:
        answer.evidence_found = False
        answer.confidence = "low"
        answer.confidence_score = 0.0
        answer.standards = []
        answer.certification = None
        answer.testing = None
        answer.answer = INSUFFICIENT_EVIDENCE_MESSAGE
        notes.append("No evidence retrieved; the assistant declined to answer.")

    answer.guardrail_notes = notes
    return answer


def insufficient_evidence_answer(question: str, language: str = "en") -> AssistantAnswer:
    """The response used whenever the corpus cannot support an answer."""
    return AssistantAnswer(
        answer=(
            f"{INSUFFICIENT_EVIDENCE_MESSAGE}\n\n"
            "The indexed BIS knowledge base does not contain material that answers this "
            "question. Rather than guess, here is what would help: give the product name, "
            "the material, and what it is used for; or give the IS number you are asking "
            "about. You can also browse the standards catalogue or the BIS services pages."
        ),
        intent="insufficient_evidence",
        language=language,  # type: ignore[arg-type]
        evidence_found=False,
        confidence="low",
        confidence_score=0.0,
        next_steps=[
            "Search the standards catalogue directly",
            "Describe your product in more detail (material, use, users)",
            "Browse BIS services for certification, testing or hallmarking",
            "Ask another question",
        ],
        guardrail_notes=[f"No usable evidence retrieved for: {question[:120]}"],
    )
