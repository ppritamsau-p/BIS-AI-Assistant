"""Clause-aware chunking.

Naive fixed-window chunking destroys the one thing a BIS answer needs most: the ability
to say "clause 5.2, page 27". So the chunker splits on clause headings first and only
falls back to a sliding window when a clause is too long to embed as one unit. Every
emitted chunk carries the clause/section/page it came from.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from backend.retrieval.text import clean_text

# "5.2 Material" / "5.2.1  Thickness" / "Annex A" / "Table 3"
CLAUSE_RE = re.compile(r"^\s{0,6}(\d{1,2}(?:\.\d{1,2}){0,3})\s+(?=[A-Z(])", re.MULTILINE)
ANNEX_RE = re.compile(r"^\s{0,6}(ANNEX\s+[A-Z])\b", re.MULTILINE | re.IGNORECASE)
PAGE_MARKER_RE = re.compile(r"<<<PAGE:(\d+)>>>")

TARGET_CHARS = 1100
OVERLAP_CHARS = 180
MIN_CHARS = 120


@dataclass
class Chunk:
    content: str
    page: int | None = None
    section: str | None = None
    clause: str | None = None
    heading: str | None = None


def _heading_for(body: str) -> str | None:
    first = body.strip().splitlines()[0] if body.strip() else ""
    first = first.strip()
    return first[:120] if 0 < len(first) <= 120 else None


def _window(text: str) -> list[str]:
    """Sliding window with overlap, cutting on sentence boundaries where possible."""
    if len(text) <= TARGET_CHARS:
        return [text]

    parts: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + TARGET_CHARS, len(text))
        if end < len(text):
            # Prefer to break after a sentence or a newline near the window edge.
            window = text[start:end]
            for sep in (". ", ".\n", "\n\n", "\n", "; "):
                cut = window.rfind(sep)
                if cut > TARGET_CHARS * 0.55:
                    end = start + cut + len(sep)
                    break
        parts.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - OVERLAP_CHARS, start + 1)
    return [p for p in parts if p]


def chunk_document(text: str, *, default_page: int | None = None) -> list[Chunk]:
    """Split a document into citable chunks.

    ``text`` may contain ``<<<PAGE:n>>>`` markers (emitted by the PDF extractor) which are
    consumed here to attach page numbers and then stripped from the stored content.
    """
    text = clean_text(text)
    if not text:
        return []

    # Track page number by character offset.
    page_at: list[tuple[int, int]] = []
    offset = 0
    cleaned_parts: list[str] = []
    cursor = 0
    for m in PAGE_MARKER_RE.finditer(text):
        cleaned_parts.append(text[cursor : m.start()])
        offset += m.start() - cursor
        page_at.append((offset, int(m.group(1))))
        cursor = m.end()
    cleaned_parts.append(text[cursor:])
    body = "".join(cleaned_parts)

    def page_for(pos: int) -> int | None:
        current = default_page
        for start, page in page_at:
            if start <= pos:
                current = page
            else:
                break
        return current

    # Locate clause / annex boundaries.
    boundaries: list[tuple[int, str]] = []
    for m in CLAUSE_RE.finditer(body):
        boundaries.append((m.start(), m.group(1)))
    for m in ANNEX_RE.finditer(body):
        boundaries.append((m.start(), m.group(1).title()))
    boundaries.sort()

    segments: list[tuple[int, str | None, str]] = []
    if not boundaries:
        segments.append((0, None, body))
    else:
        if boundaries[0][0] > 0:
            segments.append((0, None, body[: boundaries[0][0]]))
        for i, (pos, clause) in enumerate(boundaries):
            end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(body)
            segments.append((pos, clause, body[pos:end]))

    chunks: list[Chunk] = []
    for pos, clause, segment in segments:
        segment = segment.strip()
        if len(segment) < MIN_CHARS and chunks:
            # Fold tiny fragments (headings, stray lines) into the previous chunk.
            chunks[-1].content = f"{chunks[-1].content}\n{segment}".strip()
            continue
        if not segment:
            continue
        section = clause.split(".")[0] if clause and clause[0].isdigit() else clause
        for piece in _window(segment):
            chunks.append(
                Chunk(
                    content=piece,
                    page=page_for(pos),
                    section=section,
                    clause=clause,
                    heading=_heading_for(piece),
                )
            )

    return chunks
