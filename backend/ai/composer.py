"""The answer pipeline.

    question -> intent -> product understanding -> query expansion -> hybrid retrieval
             -> standard ranking -> structured lookups -> narrative composition
             -> guardrail verification -> confidence scoring -> structured answer

Two composers produce the narrative:

``compose_with_llm``
    Claude, given only the retrieved evidence, returning the structured JSON contract.

``compose_extractive``
    The fallback when no API key is configured or the model call fails. It writes the
    narrative from the retrieved passages and the structured catalogue records only, so it
    is incapable of inventing BIS content -- which makes it a genuine no-hallucination
    baseline rather than a degraded mode.

Both are passed through the same guardrails and the same confidence scorer.
"""
from __future__ import annotations

from typing import Any, Callable, Iterator

from backend.ai import guardrails
from backend.ai.confidence import score_evidence
from backend.ai.intent import (
    build_retrieval_query,
    detect_intent,
    looks_like_product_description,
    understand_product,
)
from backend.ai.llm import LLMUnavailable, get_llm
from backend.ai.prompts import build_user_turn
from backend.database.store import KnowledgeBase
from backend.models.schemas import (
    AssistantAnswer,
    CertificationInfo,
    EvidenceChunk,
    ProductUnderstanding,
    SourceRef,
    Standard,
    StandardMatch,
    TestingInfo,
)
from backend.config import settings

MAX_SOURCES = 8


# ==========================================================================
# Standard ranking
# ==========================================================================
def rank_standards(
    kb: KnowledgeBase,
    chunks: list[EvidenceChunk],
    product: ProductUnderstanding | None,
    limit: int = 5,
) -> list[StandardMatch]:
    """Aggregate chunk-level evidence into standard-level recommendations.

    A standard's relevance is the strength of its best supporting passage, lifted by how
    many distinct passages support it, and then by explicit product-profile agreement.
    Every factor that contributed is recorded so the UI can answer "why this standard?".
    """
    grouped: dict[str, list[EvidenceChunk]] = {}
    for chunk in chunks:
        if chunk.standard_number:
            grouped.setdefault(chunk.standard_number.upper(), []).append(chunk)

    if not grouped:
        return []

    matches: list[StandardMatch] = []
    for number, group in grouped.items():
        std = kb.get_standard(number)
        if std is None:
            continue

        group.sort(key=lambda c: c.score, reverse=True)
        best = group[0].score
        support = min(len(group) / 3.0, 1.0)
        base = 0.75 * min(best / 1.4, 1.0) + 0.25 * support

        reasons: list[str] = []
        factors: dict[str, bool] = {}

        if product:
            cat_match = bool(product.category) and product.category.lower() == std.category.lower()
            factors["Product category match"] = cat_match
            if cat_match:
                base += 0.16
                reasons.append(f"Category matches: {std.category}.")

            mat_match = bool(product.materials) and any(
                m.lower() in " ".join(std.materials).lower() for m in product.materials
            )
            factors["Material match"] = mat_match
            if mat_match:
                base += 0.10
                reasons.append(
                    "Material matches the standard's declared materials: "
                    f"{', '.join(product.materials)}."
                )

            use_match = bool(product.intended_use) and any(
                word in " ".join(std.intended_use).lower()
                for word in product.intended_use.lower().split()
                if len(word) > 3
            )
            factors["Intended-use match"] = use_match
            if use_match:
                base += 0.08
                reasons.append(f"Intended use matches: {product.intended_use}.")

            scope_match = bool(product.product) and any(
                word in std.scope.lower()
                for word in product.product.lower().split()
                if len(word) > 3
            )
            factors["Scope match"] = scope_match
            if scope_match:
                base += 0.06
                reasons.append("The product appears in the standard's scope clause.")

        anchored = [c for c in group if c.clause or c.page]
        if anchored:
            top = anchored[0]
            locator = ", ".join(
                filter(None, [f"clause {top.clause}" if top.clause else None,
                              f"page {top.page}" if top.page else None])
            )
            reasons.append(f"Supported by retrieved text at {locator}.")

        if not reasons:
            reasons.append("Matched on the retrieved text of this standard.")

        matches.append(
            StandardMatch(
                standard=std,
                relevance=round(min(base, 0.99), 3),
                reasons=reasons,
                match_factors=factors,
                sources=[c.to_source() for c in group[:3]],
            )
        )

    matches.sort(key=lambda m: m.relevance, reverse=True)
    return matches[:limit]


# Questions about a *process* (how do I certify, where do I test, is this genuine) retrieve
# procedure documents, and whichever product standard happens to sit nearby gets dragged
# along with a mediocre score. Showing it as a recommendation implies the assistant decided
# the question was about that product, which it did not. So on process intents a standard
# has to clear a high bar before it is presented as applicable.
PROCESS_INTENTS = {"certification", "laboratory", "consumer", "hallmarking", "general"}
PROCESS_RELEVANCE_FLOOR = 0.75


def filter_matches_for_intent(
    matches: list[StandardMatch], intent: str, product: ProductUnderstanding | None
) -> list[StandardMatch]:
    if intent not in PROCESS_INTENTS or (product and product.product):
        return matches
    return [m for m in matches if m.relevance >= PROCESS_RELEVANCE_FLOOR]


# ==========================================================================
# Structured sections
# ==========================================================================
def build_certification(
    kb: KnowledgeBase, matches: list[StandardMatch], product: ProductUnderstanding | None
) -> CertificationInfo | None:
    top = matches[0].standard if matches else None
    schemes = kb.schemes_for(
        category=(product.category if product else None) or (top.category if top else None),
        standard_number=top.standard_number if top else None,
    )
    if not schemes and top is None:
        return None

    scheme = schemes[0] if schemes else None

    if top is not None and top.certification_required is True:
        required = "Mandatory where notified under a QCO or CRS - verify against the official list"
    elif top is not None and top.certification_required is False:
        required = "Voluntary unless the product is notified under a QCO"
    else:
        required = "Not established from evidence"

    return CertificationInfo(
        required=required,
        scheme=(scheme.scheme_name if scheme else (top.certification_scheme if top else None)),
        process=(scheme.procedure if scheme else []),
        documents=(scheme.documents if scheme else []),
        inspection=(scheme.inspection if scheme else None),
        verified=bool(scheme) or (top is not None and top.certification_required is not None),
    )


def build_testing(kb: KnowledgeBase, matches: list[StandardMatch]) -> TestingInfo | None:
    if not matches:
        return None
    std = matches[0].standard
    tests = [t.strip() for t in (std.testing_summary or "").split(",") if t.strip()]
    labs = kb.labs_for_standard(std.standard_number, limit=3)
    if not tests and not labs:
        return None
    return TestingInfo(
        tests=tests,
        laboratory_category=(labs[0].lab_type if labs else None),
        laboratories=labs,
        verified=bool(tests),
    )


def collect_sources(chunks: list[EvidenceChunk], limit: int = MAX_SOURCES) -> list[SourceRef]:
    seen: set[tuple] = set()
    sources: list[SourceRef] = []
    for chunk in chunks:
        key = (chunk.standard_number, chunk.clause, chunk.page, chunk.title)
        if key in seen:
            continue
        seen.add(key)
        sources.append(chunk.to_source())
        if len(sources) >= limit:
            break
    return sources


# ==========================================================================
# Narrative composition
# ==========================================================================
def _structured_context(matches: list[StandardMatch], cert: CertificationInfo | None) -> str:
    lines: list[str] = []
    for m in matches:
        s = m.standard
        lines.append(
            f"- {s.standard_number} ({s.status}, {s.publication_date}): {s.title}. "
            f"Category: {s.category}. Scope: {s.scope[:220]}"
        )
    if cert:
        lines.append(f"- Certification status from catalogue: {cert.required}")
        if cert.scheme:
            lines.append(f"- Applicable scheme: {cert.scheme}")
    return "\n".join(lines)


def compose_with_llm(
    question: str,
    chunks: list[EvidenceChunk],
    matches: list[StandardMatch],
    cert: CertificationInfo | None,
    product: ProductUnderstanding | None,
    language: str,
    intent: str,
) -> tuple[str, dict[str, Any]]:
    llm = get_llm()
    turn = build_user_turn(
        question,
        chunks,
        language=language,
        intent=intent,
        extra_context=_structured_context(matches, cert),
    )
    payload = llm.complete_json(turn)
    answer_text = (payload.get("answer") or "").strip()
    if not answer_text:
        raise LLMUnavailable("model returned no answer text")
    return answer_text, payload


def compose_extractive(
    question: str,
    chunks: list[EvidenceChunk],
    matches: list[StandardMatch],
    cert: CertificationInfo | None,
    testing: TestingInfo | None,
    product: ProductUnderstanding | None,
    intent: str,
    language: str,
) -> str:
    """Write the answer from retrieved text and catalogue records only."""
    parts: list[str] = []

    if product and product.product:
        bits = [f"**{product.product}**"]
        if product.category:
            bits.append(f"category *{product.category}*")
        if product.materials:
            bits.append(f"material *{', '.join(product.materials)}*")
        parts.append("From your description I understood: " + ", ".join(bits) + ".")

    if matches:
        lead = matches[0].standard
        # Prefer a localised summary when the catalogue carries one.
        summary = {
            "hi": lead.summary_hi, "bn": lead.summary_bn
        }.get(language) or lead.scope or lead.title
        parts.append(
            f"The closest match in the indexed knowledge base is **{lead.standard_number} - "
            f"{lead.title}** ({lead.status}, {lead.publication_date}). {summary}"
        )
        if len(matches) > 1:
            others = ", ".join(m.standard.standard_number for m in matches[1:])
            parts.append(f"Other standards that also matched: {others}.")
    else:
        parts.append(
            "No specific Indian Standard in the indexed knowledge base matched closely enough "
            "to recommend. The passages below are the most relevant material found."
        )

    top = chunks[0] if chunks else None
    if top:
        # Catalogue and guideline chunks carry no clause or page, so fall back to whatever
        # identifies them -- an empty "From the source ()" is worse than no locator at all.
        locator = ", ".join(
            filter(None, [
                top.standard_number,
                f"clause {top.clause}" if top.clause else None,
                f"page {top.page}" if top.page else None,
            ])
        ) or " - ".join(filter(None, [top.title, top.document_type]))
        excerpt = top.content.strip().replace("\n", " ")
        if len(excerpt) > 420:
            excerpt = excerpt[:420].rsplit(" ", 1)[0] + "..."
        parts.append(f"From the source ({locator}):\n\n> {excerpt}")

    if cert:
        cert_lines = [f"**Certification:** {cert.required}"]
        if cert.scheme:
            cert_lines.append(f"Applicable scheme: {cert.scheme}.")
        cert_lines.append(
            "An Indian Standard existing for a product does not by itself make certification "
            "mandatory - that depends on whether the product is notified under a Quality "
            "Control Order or the Compulsory Registration Scheme."
        )
        parts.append(" ".join(cert_lines))

    if testing and testing.tests:
        parts.append("**Testing indicated by the catalogue record:** " + "; ".join(testing.tests) + ".")

    if not settings.llm_enabled:
        parts.append(
            "*This answer was assembled directly from the retrieved passages (no language "
            "model is configured). It is quoted and summarised from the sources listed below "
            "and contains nothing beyond them.*"
        )

    return "\n\n".join(parts)


def default_next_steps(intent: str, matches: list[StandardMatch]) -> list[str]:
    number = matches[0].standard.standard_number if matches else "the applicable standard"
    if intent == "hallmarking":
        return [
            "Check whether your articles fall under the hallmarking requirement",
            "Register as a jeweller with BIS for each premises",
            "Identify a BIS recognised Assaying and Hallmarking Centre",
            "Send articles for assaying and hallmarking with HUID",
        ]
    if intent == "laboratory":
        return [
            "Confirm the applicable Indian Standard for your product",
            "Identify the specific tests required by that standard",
            "Search recognised laboratories filtered by that standard and your state",
            "Confirm the laboratory's recognised scope covers your product",
        ]
    if intent == "consumer":
        return [
            "Check the mark and the licence or registration number on the product",
            "Verify the number against the official BIS database or BIS Care",
            "Keep the invoice",
            "Lodge a complaint with BIS if the mark cannot be verified",
        ]
    return [
        f"Confirm that {number} covers your exact product variant",
        "Check whether the product is notified under a QCO or CRS",
        "Get samples tested at a BIS recognised laboratory",
        "Prepare the technical and legal documents",
        "Submit the application through the BIS online portal",
    ]


# ==========================================================================
# Entry point
# ==========================================================================
def answer_question(
    kb: KnowledgeBase,
    question: str,
    *,
    language: str = "en",
    forced_intent: str | None = None,
    limit: int = 5,
    on_stage: Callable[[str, dict[str, Any]], None] | None = None,
) -> AssistantAnswer:
    def stage(name: str, **data: Any) -> None:
        if on_stage:
            on_stage(name, data)

    question = (question or "").strip()
    if not question:
        return guardrails.insufficient_evidence_answer(question, language)

    intent = forced_intent or detect_intent(question)
    stage("intent", intent=intent)

    product: ProductUnderstanding | None = None
    if intent in {"product_standard", "compliance"} or looks_like_product_description(question):
        product = understand_product(question)
        llm = get_llm()
        if llm.available:
            try:
                enriched = llm.enrich_product(question)
                product = ProductUnderstanding(
                    product=enriched.get("product") or product.product,
                    category=enriched.get("category") or product.category,
                    materials=enriched.get("materials") or product.materials,
                    intended_use=enriched.get("intended_use") or product.intended_use,
                    industry=enriched.get("industry") or product.industry,
                    target_user=enriched.get("target_user") or product.target_user,
                    characteristics=enriched.get("characteristics") or product.characteristics,
                    notes=product.notes,
                )
            except LLMUnavailable:
                pass  # rule-based profile already in hand
        stage("product", product=product.model_dump())

    query = build_retrieval_query(question, product)
    stage("retrieving", query=query)

    chunks = kb.retriever.retrieve(query, limit=settings.retrieval_top_k)
    chunks = [c for c in chunks if c.score >= settings.min_evidence_score]
    stage("retrieved", count=len(chunks))

    if not chunks:
        answer = guardrails.insufficient_evidence_answer(question, language)
        kb.log_query({"query": question, "intent": intent, "confidence": "low",
                      "evidence_count": 0, "top_score": 0.0})
        return answer

    matches = rank_standards(kb, chunks, product, limit=limit)
    matches = filter_matches_for_intent(matches, intent, product)
    cert = build_certification(kb, matches, product)
    testing = build_testing(kb, matches)
    stage("ranked", standards=[m.standard.standard_number for m in matches])

    generator = "extractive"
    llm_payload: dict[str, Any] = {}
    answer_text = ""

    llm = get_llm()
    if llm.available:
        stage("composing", generator="claude")
        try:
            answer_text, llm_payload = compose_with_llm(
                question, chunks, matches, cert, product, language, intent
            )
            generator = f"claude:{llm.model}"
        except LLMUnavailable as exc:
            stage("llm_fallback", reason=str(exc))

    if not answer_text:
        stage("composing", generator="extractive")
        answer_text = compose_extractive(
            question, chunks, matches, cert, testing, product, intent, language
        )

    # Merge anything the model added on top of the deterministic sections.
    why_match = llm_payload.get("why_match") or [
        r for m in matches[:2] for r in m.reasons
    ][:6]
    next_steps = llm_payload.get("next_steps") or default_next_steps(intent, matches)
    documents = (
        (llm_payload.get("certification") or {}).get("documents")
        if isinstance(llm_payload.get("certification"), dict)
        else None
    ) or (cert.documents if cert else [])

    if isinstance(llm_payload.get("testing"), dict) and testing:
        extra_tests = llm_payload["testing"].get("tests") or []
        for t in extra_tests:
            if t not in testing.tests:
                testing.tests.append(t)

    confidence, score, factors = score_evidence(chunks)

    answer = AssistantAnswer(
        answer=answer_text,
        intent=intent,
        language=language,  # type: ignore[arg-type]
        product_understanding=product,
        standards=matches,
        why_match=why_match,
        certification=cert,
        testing=testing,
        documents=documents,
        next_steps=next_steps,
        sources=collect_sources(chunks),
        confidence=confidence,
        confidence_score=score,
        evidence_found=bool(llm_payload.get("evidence_found", True)),
        generator=generator,
        guardrail_notes=factors,
    )

    answer = guardrails.verify_answer(answer, chunks)
    stage("verified", notes=len(answer.guardrail_notes))

    kb.log_query(
        {
            "query": question,
            "intent": intent,
            "confidence": answer.confidence,
            "evidence_count": len(chunks),
            "top_score": chunks[0].score if chunks else 0.0,
            "generator": generator,
        }
    )
    return answer


def answer_with_stages(
    kb: KnowledgeBase, question: str, **kwargs: Any
) -> Iterator[tuple[str, dict[str, Any]]]:
    """Run the pipeline, yielding each stage the moment it completes.

    Used by the SSE endpoint so the UI can show the retrieval pipeline progressing rather
    than a spinner. The pipeline runs on a worker thread and pushes real stage events into
    a queue as they occur -- these are the actual stages emitted from inside
    `answer_question`, not a replay staged after the fact.
    """
    import queue
    import threading

    events: "queue.Queue[tuple[str, dict[str, Any]] | None]" = queue.Queue()
    result: dict[str, Any] = {}

    def run() -> None:
        try:
            answer = answer_question(
                kb, question, on_stage=lambda name, data: events.put((name, data)), **kwargs
            )
            result["answer"] = answer.model_dump(mode="json")
        except Exception as exc:  # surfaced to the client as an error event
            result["error"] = str(exc)
        finally:
            events.put(None)

    worker = threading.Thread(target=run, daemon=True)
    worker.start()

    while True:
        event = events.get()
        if event is None:
            break
        yield event

    worker.join(timeout=1)
    if "error" in result:
        yield "error", {"message": result["error"]}
    else:
        yield "answer", result.get("answer", {})
