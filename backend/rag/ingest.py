"""Document ingestion pipeline.

    PDF -> text extraction -> OCR (only for pages that came back empty)
        -> cleaning -> clause-aware chunking -> metadata extraction -> embeddings

PDF and OCR dependencies are optional. If `pypdf` is missing the pipeline still accepts
plain text and Markdown, and reports a clear reason rather than failing silently -- which
matters because a silently skipped document would leave the assistant answering from an
incomplete knowledge base without saying so.
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from pathlib import Path

from backend.rag.chunker import Chunk, chunk_document
from backend.retrieval.text import clean_text, extract_standard_numbers

TITLE_HINT_RE = re.compile(r"^\s*(?:indian standard|भारतीय मानक)\s*[\n:-]+\s*(.{5,140})", re.IGNORECASE)
YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


@dataclass
class ExtractedDocument:
    filename: str
    text: str
    pages: int
    standard_number: str | None
    title: str | None
    edition: str | None
    ocr_pages: list[int]
    warnings: list[str]


# --------------------------------------------------------------------------
# Extraction
# --------------------------------------------------------------------------
def _extract_pdf(path: Path) -> tuple[list[str], list[str]]:
    """Return per-page text plus any warnings. Raises if pypdf is unavailable."""
    from pypdf import PdfReader  # noqa: PLC0415

    warnings: list[str] = []
    reader = PdfReader(str(path))
    pages: list[str] = []
    for i, page in enumerate(reader.pages, start=1):
        try:
            pages.append(page.extract_text() or "")
        except Exception as exc:
            pages.append("")
            warnings.append(f"page {i}: extraction failed ({exc})")
    return pages, warnings


def _ocr_page(path: Path, page_number: int) -> str:
    """OCR a single page. Optional -- returns '' when the toolchain is absent."""
    try:
        import pytesseract  # noqa: PLC0415
        from pdf2image import convert_from_path  # noqa: PLC0415
    except ImportError:
        return ""
    try:
        images = convert_from_path(str(path), first_page=page_number, last_page=page_number, dpi=300)
        if not images:
            return ""
        return pytesseract.image_to_string(images[0]) or ""
    except Exception:
        return ""


def extract_document(path: Path, *, enable_ocr: bool = True) -> ExtractedDocument:
    path = Path(path)
    warnings: list[str] = []
    ocr_pages: list[int] = []

    if path.suffix.lower() == ".pdf":
        try:
            pages, warnings = _extract_pdf(path)
        except ImportError:
            raise RuntimeError(
                "PDF ingestion needs `pypdf`. Install it with `pip install pypdf`, "
                "or ingest a .txt/.md export of the document instead."
            ) from None

        if enable_ocr:
            for i, page_text in enumerate(pages, start=1):
                # A page with almost no extractable text is very likely a scan.
                if len(page_text.strip()) < 40:
                    ocr_text = _ocr_page(path, i)
                    if ocr_text.strip():
                        pages[i - 1] = ocr_text
                        ocr_pages.append(i)
            scanned = [i for i, p in enumerate(pages, 1) if len(p.strip()) < 40]
            if scanned and not ocr_pages:
                warnings.append(
                    f"{len(scanned)} page(s) yielded no text and OCR is unavailable "
                    "(install pytesseract + pdf2image + Tesseract to index scanned pages)"
                )
    else:
        pages = [path.read_text(encoding="utf-8", errors="replace")]

    marked = "\n".join(f"<<<PAGE:{i}>>>\n{text}" for i, text in enumerate(pages, start=1))
    text = clean_text(marked)

    head = "\n".join(text.splitlines()[:60])
    standards = extract_standard_numbers(head) or extract_standard_numbers(path.stem)
    title_match = TITLE_HINT_RE.search(head)
    years = YEAR_RE.findall(head)

    return ExtractedDocument(
        filename=path.name,
        text=text,
        pages=len(pages),
        standard_number=standards[0] if standards else None,
        title=(title_match.group(1).strip() if title_match else None),
        edition=(years[0] if years else None),
        ocr_pages=ocr_pages,
        warnings=warnings,
    )


# --------------------------------------------------------------------------
# Chunk records
# --------------------------------------------------------------------------
def build_chunk_records(
    doc: ExtractedDocument,
    *,
    standard_number: str | None = None,
    title: str | None = None,
    document_type: str = "Indian Standard",
    source_url: str | None = None,
    document_id: str | None = None,
) -> list[dict]:
    """Chunk an extracted document into the metadata shape stored in the index."""
    document_id = document_id or uuid.uuid4().hex[:12]
    std = standard_number or doc.standard_number
    doc_title = title or doc.title or doc.filename

    records: list[dict] = []
    chunks: list[Chunk] = chunk_document(doc.text)
    for i, chunk in enumerate(chunks):
        records.append(
            {
                "chunk_id": f"{document_id}:{i:04d}",
                "document_id": document_id,
                "standard_number": std,
                "title": doc_title,
                "content": chunk.content,
                "page": chunk.page,
                "section": chunk.section,
                "clause": chunk.clause,
                "heading": chunk.heading,
                "document_type": document_type,
                "source": "BIS",
                "source_url": source_url,
            }
        )
    return records
