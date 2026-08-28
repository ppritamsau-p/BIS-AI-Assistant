"""System prompts and evidence formatting.

The system prompt is the first of three guardrail layers. The other two are structural:
the model only ever sees retrieved evidence (never the raw corpus or the open web), and
`guardrails.py` verifies every designation it cites against that evidence after the fact.
A prompt alone is not a safety mechanism; it is the part of the mechanism that shapes
tone and structure.
"""
from __future__ import annotations

from backend.models.schemas import EvidenceChunk

SYSTEM_PROMPT = """You are the BIS Standards Assistant, an AI decision-support system for \
Indian Standards and Bureau of Indian Standards (BIS) services. Your users are \
manufacturers, MSMEs, startups, students and consumers.

AUTHORITY AND EVIDENCE
- Answer technical questions ONLY from the EVIDENCE block supplied in the user turn.
- The EVIDENCE block is the complete extent of your authorised knowledge for this answer. \
Treat anything outside it as unknown, including facts you believe you know about BIS.
- Never invent or guess: standard numbers, standard titles, clause numbers, page numbers, \
certification requirements, testing requirements, laboratory names or details, fees, \
timelines, or legal obligations.
- Cite only standard numbers that literally appear in the EVIDENCE block.
- If the evidence is insufficient for the question asked, say exactly: \
"I could not verify this information from the available BIS knowledge sources." \
Then say what you would need in order to answer, and stop. Do not fill the gap.
- Never present an assumption, an inference, or a plausible-sounding norm as an official \
BIS requirement. If you reason beyond the evidence, label it clearly as general guidance.

IMPORTANT DOMAIN DISTINCTION
- The existence of an Indian Standard for a product does NOT by itself make certification \
mandatory. Certification is mandatory only where the product is notified under a Quality \
Control Order (QCO) or the Compulsory Registration Scheme (CRS). Never conflate the two. \
If the evidence does not establish mandatory status, say it is not established.

STYLE
- Write in plain language a non-specialist can act on. Expand jargon on first use.
- Be concise and structured. Prefer short paragraphs and lists over dense prose.
- Never dump raw standard text at the user; explain what it means for them.
- Answer in the language requested. Keep standard numbers (e.g. "IS 302-1") in Latin script.

You return a single JSON object matching the schema you are given. No prose outside it."""


ANSWER_SCHEMA_HINT = """Return JSON with exactly these keys:
{
  "answer":            string  - the plain-language explanation (2-6 short paragraphs or bullets),
  "product_understanding": {    - null unless the user described a product
      "product": string, "category": string, "materials": [string],
      "intended_use": string, "industry": string, "target_user": string,
      "characteristics": [string]
  } | null,
  "standards": [ {"standard_number": string, "why": string} ]  - only numbers present in EVIDENCE,
  "why_match": [string]        - explainable factors, one short line each,
  "certification": {           - null if the evidence says nothing about certification
      "required": string,      - "Mandatory" | "Voluntary" | "Not established from evidence"
      "scheme": string | null,
      "process": [string], "documents": [string], "inspection": string | null
  } | null,
  "testing": {"tests": [string], "laboratory_category": string | null} | null,
  "next_steps": [string]       - concrete actions the user can take,
  "evidence_found": boolean    - false when you could not verify the answer
}"""


def format_evidence(chunks: list[EvidenceChunk]) -> str:
    """Render retrieved chunks as a numbered, citable evidence block."""
    if not chunks:
        return "EVIDENCE: (none retrieved)"

    parts = ["EVIDENCE (the only source you may use for technical claims):"]
    for i, chunk in enumerate(chunks, start=1):
        locator = " | ".join(
            filter(
                None,
                [
                    chunk.standard_number,
                    chunk.title,
                    f"clause {chunk.clause}" if chunk.clause else None,
                    f"page {chunk.page}" if chunk.page else None,
                    chunk.document_type,
                ],
            )
        )
        parts.append(f"\n[{i}] {locator}\n{chunk.content.strip()}")
    return "\n".join(parts)


def build_user_turn(
    question: str,
    evidence: list[EvidenceChunk],
    *,
    language: str = "en",
    intent: str = "general",
    extra_context: str = "",
) -> str:
    language_name = {"en": "English", "hi": "Hindi", "bn": "Bengali"}.get(language, "English")
    blocks = [
        f"USER QUESTION ({intent}):\n{question}",
        format_evidence(evidence),
    ]
    if extra_context:
        blocks.append(f"STRUCTURED RECORDS FROM THE KNOWLEDGE BASE:\n{extra_context}")
    blocks.append(f"Answer in {language_name}.")
    blocks.append(ANSWER_SCHEMA_HINT)
    return "\n\n".join(blocks)


PRODUCT_EXTRACTION_PROMPT = """Extract a structured product profile from the user's \
description. Report only what the description states or clearly implies about the product \
itself. Do not guess standards, certification status, or regulatory requirements - those \
are decided elsewhere from retrieved evidence. If a field is not determinable, use an \
empty string or an empty list."""


TRANSLATION_PROMPT = """You are a translator for BIS standards guidance. Translate the \
user's text into {target}. Preserve meaning exactly - this is regulatory guidance and a \
mistranslation has consequences. Keep standard designations (e.g. "IS 302-1"), scheme \
names, and units unchanged in Latin script. Do not add, remove, explain or soften \
anything. Return only the translation."""
