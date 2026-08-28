"""Compliance checklist and standards comparison.

Both build their output from retrieved evidence and catalogue records. Where a value is
not present in the knowledge base they emit an explicit "Not available in the indexed
knowledge base" rather than a plausible guess -- an empty cell in a comparison table is
information; a fabricated one is a liability.
"""
from __future__ import annotations

from backend.ai.composer import answer_question, collect_sources
from backend.database.store import KnowledgeBase
from backend.models.schemas import (
    ComplianceChecklist,
    ComplianceItem,
    CompareResponse,
    CompareRow,
    SourceRef,
    Standard,
)

NOT_AVAILABLE = "Not available in the indexed knowledge base"

BASE_CHECKLIST: list[tuple[str, str]] = [
    ("identify-standard", "Identify the applicable Indian Standard"),
    ("check-mandatory", "Check whether certification is mandatory (QCO / CRS)"),
    ("identify-scheme", "Identify the applicable BIS certification scheme"),
    ("prepare-documents", "Prepare the technical and legal documents"),
    ("conduct-testing", "Conduct the required testing"),
    ("select-lab", "Select an appropriate BIS recognised laboratory"),
    ("submit-application", "Submit the application through the BIS portal"),
    ("inspection", "Complete the inspection requirements"),
    ("resolve-nc", "Resolve any non-conformities raised"),
    ("obtain-licence", "Obtain the certification / licence"),
]


def generate_checklist(
    kb: KnowledgeBase, product: str, standard_number: str | None = None, language: str = "en"
) -> ComplianceChecklist:
    """Build a checklist grounded in what the knowledge base actually knows."""
    answer = answer_question(kb, product, language=language, forced_intent="compliance")

    std: Standard | None = None
    if standard_number:
        std = kb.get_standard(standard_number)
    if std is None and answer.standards:
        std = answer.standards[0].standard

    scheme = None
    if std:
        schemes = kb.schemes_for(category=std.category, standard_number=std.standard_number)
        scheme = schemes[0] if schemes else None

    labs = kb.labs_for_standard(std.standard_number if std else None, limit=2)
    source_by_std = {s.standard_number: s for s in answer.sources if s.standard_number}

    details: dict[str, str] = {
        "identify-standard": (
            f"{std.standard_number} - {std.title}" if std
            else "No standard could be matched from the indexed knowledge base for this product."
        ),
        "check-mandatory": (
            "An Indian Standard existing for a product does not by itself make certification "
            "mandatory. Confirm whether the product is notified under a Quality Control Order "
            "or the Compulsory Registration Scheme against the official BIS list."
        ),
        "identify-scheme": (scheme.scheme_name if scheme else NOT_AVAILABLE),
        "prepare-documents": (
            "; ".join(scheme.documents[:5]) if scheme and scheme.documents else NOT_AVAILABLE
        ),
        "conduct-testing": (std.testing_summary if std and std.testing_summary else NOT_AVAILABLE),
        "select-lab": (
            "; ".join(f"{lab.name} ({lab.state})" for lab in labs) if labs
            else "No laboratory in the indexed dataset lists this standard in its scope."
        ),
        "submit-application": (
            "; ".join(scheme.procedure[5:8]) if scheme and len(scheme.procedure) > 5
            else "Submit through the BIS online portal with the prescribed fee."
        ),
        "inspection": (scheme.inspection if scheme and scheme.inspection else NOT_AVAILABLE),
        "resolve-nc": "Address every non-conformity raised during inspection or testing before the licence can be granted.",
        "obtain-licence": (
            "The licence permits use of the Standard Mark for the covered product only, "
            "subject to the Scheme of Testing and Inspection and ongoing surveillance."
        ),
    }

    items = [
        ComplianceItem(
            id=key,
            label=label,
            detail=details.get(key, ""),
            completed=False,
            source=(source_by_std.get(std.standard_number) if std and key == "identify-standard" else None),
        )
        for key, label in BASE_CHECKLIST
    ]

    return ComplianceChecklist(
        product=product,
        standard_number=(std.standard_number if std else None),
        items=items,
        completed=0,
        total=len(items),
        sources=answer.sources,
    )


# --------------------------------------------------------------------------
# Comparison
# --------------------------------------------------------------------------
COMPARE_ROWS: list[tuple[str, str]] = [
    ("Product Scope", "scope"),
    ("Category", "category"),
    ("Industry", "industry"),
    ("Material", "materials"),
    ("Intended Use", "intended_use"),
    ("Status", "status"),
    ("Edition / Year", "edition_year"),
    ("Requirements", "requirements"),
    ("Testing", "testing_summary"),
    ("Certification", "certification"),
    ("Related Standards", "related_standards"),
]


def _value(kb: KnowledgeBase, std: Standard, field: str) -> str:
    if field == "materials":
        return ", ".join(std.materials) or NOT_AVAILABLE
    if field == "intended_use":
        return ", ".join(std.intended_use) or NOT_AVAILABLE
    if field == "related_standards":
        return ", ".join(std.related_standards) or NOT_AVAILABLE
    if field == "edition_year":
        return " ".join(filter(None, [std.edition, std.publication_date])) or NOT_AVAILABLE
    if field == "certification":
        if std.certification_required is None:
            return NOT_AVAILABLE
        status = "Required where notified" if std.certification_required else "Voluntary unless notified"
        return f"{status}. Scheme: {std.certification_scheme or NOT_AVAILABLE}"
    if field == "requirements":
        # Pull the highest-scoring requirements passage actually indexed for this standard.
        chunks = kb.retriever.retrieve(
            f"{std.standard_number} requirements", limit=3, standard_filter=std.standard_number
        )
        for chunk in chunks:
            if chunk.clause and chunk.clause.startswith("5"):
                text = chunk.content.strip().replace("\n", " ")
                return (text[:300] + "...") if len(text) > 300 else text
        return NOT_AVAILABLE
    return getattr(std, field, "") or NOT_AVAILABLE


def compare_standards(kb: KnowledgeBase, numbers: list[str]) -> CompareResponse:
    standards: list[Standard] = []
    missing: list[str] = []
    for number in numbers:
        std = kb.get_standard(number)
        if std:
            standards.append(std)
        else:
            missing.append(number)

    rows = [
        CompareRow(
            parameter=label,
            values={std.standard_number: _value(kb, std, field) for std in standards},
        )
        for label, field in COMPARE_ROWS
    ]

    sources: list[SourceRef] = []
    for std in standards:
        chunks = kb.retriever.retrieve(
            std.standard_number, limit=2, standard_filter=std.standard_number
        )
        sources.extend(collect_sources(chunks, limit=2))

    if missing:
        rows.insert(
            0,
            CompareRow(
                parameter="Not found",
                values={n: "Not present in the indexed knowledge base" for n in missing},
            ),
        )

    return CompareResponse(standards=standards, rows=rows, sources=sources)
