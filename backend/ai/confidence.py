"""Evidence-confidence scoring.

This is a *retrieval* confidence signal, not a BIS rating and not a probability that the
answer is correct. It answers one narrow question: how well-supported is this answer by
the indexed corpus? Four inputs, each capturing a different failure mode:

  strength      -- the best chunk barely matched            -> weak support
  corroboration -- only one chunk matched                   -> single point of failure
  agreement     -- matches are scattered across many standards -> the query is ambiguous
  citability    -- no clause/page anchors                   -> the answer cannot be checked

The label thresholds are intentionally conservative: it is much worse to show a green
badge on a thin answer than an amber badge on a good one.
"""
from __future__ import annotations

from backend.models.schemas import Confidence, EvidenceChunk

HIGH_THRESHOLD = 0.72
MEDIUM_THRESHOLD = 0.45


def score_evidence(chunks: list[EvidenceChunk]) -> tuple[Confidence, float, list[str]]:
    """Return (label, 0..1 score, human-readable factors)."""
    if not chunks:
        return "low", 0.0, ["No supporting evidence was retrieved from the knowledge base."]

    factors: list[str] = []

    top = chunks[0].score
    # A reranked score reaches ~2.0 only when the fused rank, an exact designation match
    # and strong title/body overlap all agree, so 1.9 is the saturation point. Dividing by
    # a smaller number here made almost every answer read "high", which made the badge
    # meaningless -- the indicator is only useful if it can say "no".
    strength = min(top / 1.9, 1.0)
    factors.append(f"Top evidence match scored {top:.2f}.")

    strong = [c for c in chunks if c.score >= max(top * 0.55, 0.25)]
    corroboration = min(len(strong) / 4.0, 1.0)
    factors.append(f"{len(strong)} passage(s) independently support this answer.")

    standards = {c.standard_number for c in chunks[:5] if c.standard_number}
    if not standards:
        agreement = 0.45
        factors.append("Evidence is from guidance documents rather than a specific standard.")
    elif len(standards) == 1:
        agreement = 1.0
        factors.append(f"All top evidence points to a single standard ({next(iter(standards))}).")
    else:
        agreement = max(0.35, 1.0 - 0.18 * (len(standards) - 1))
        factors.append(f"Evidence spans {len(standards)} standards, so applicability needs narrowing.")

    anchored = [c for c in chunks if c.clause or c.page]
    citability = min(len(anchored) / max(len(chunks), 1) + 0.15, 1.0)
    if anchored:
        factors.append(f"{len(anchored)} passage(s) carry a clause or page reference.")
    else:
        factors.append("No clause or page anchors available for these passages.")

    score = 0.40 * strength + 0.25 * corroboration + 0.20 * agreement + 0.15 * citability
    score = round(min(max(score, 0.0), 1.0), 3)

    if score >= HIGH_THRESHOLD:
        label: Confidence = "high"
    elif score >= MEDIUM_THRESHOLD:
        label = "medium"
    else:
        label = "low"

    return label, score, factors


CONFIDENCE_DISCLAIMER = (
    "This is the AI system's evidence-confidence indicator based on retrieval quality. "
    "It is not an official BIS rating and does not certify compliance."
)
