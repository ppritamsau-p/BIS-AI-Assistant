"""Tokenisation shared by every retriever.

BIS queries mix two very different shapes: exact designations ("IS 302-1", "IS 15111:2002")
and free-form product prose ("steel lunch box for school children"). The tokeniser keeps
designations intact as single tokens so BM25 can match them exactly, while still emitting
the ordinary word tokens the semantic side needs.
"""
from __future__ import annotations

import re

# IS 302, IS 302-1, IS 9873 Part 3, IS 15111 : 2002, IS/ISO 9001 ...
#
# The part and the year are both written after a hyphen or colon, so they are told apart
# by width: a part is 1-3 digits, a year is exactly 4. The `(?!\d)` guard stops the part
# group from swallowing the first three digits of a year.
STANDARD_RE = re.compile(
    r"\bIS(?:\s*/\s*(?:ISO|IEC|EN))?\s*:?\s*(\d{2,5})"
    r"(?:(?:\s*[-(]\s*(?:part|pt)?\s*|\s+(?:part|pt)\s*)(\d{1,3})(?!\d)\s*\)?)?"
    r"(?:\s*[:\-]\s*((?:19|20)\d{2}))?",
    re.IGNORECASE,
)

WORD_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)

STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being", "of", "for", "to",
    "in", "on", "at", "by", "with", "from", "as", "and", "or", "but", "if", "then", "than",
    "this", "that", "these", "those", "it", "its", "i", "we", "you", "my", "our", "your",
    "can", "could", "should", "would", "will", "shall", "may", "might", "do", "does", "did",
    "have", "has", "had", "how", "what", "which", "who", "whom", "when", "where", "why",
    "about", "into", "over", "under", "please", "tell", "me", "get", "want", "need", "any",
}

# Light domain-aware stemming: enough to fold plurals and common suffixes without a
# dependency on a full stemmer.
_SUFFIXES = ("ational", "ization", "isation", "ements", "ement", "ments", "ment", "ings",
             "ing", "ies", "ers", "er", "ed", "es", "s")

SYNONYMS: dict[str, tuple[str, ...]] = {
    "bottle": ("flask", "container", "vessel"),
    "flask": ("bottle", "vacuum", "container"),
    "lunchbox": ("tiffin", "lunch", "box", "container"),
    "tiffin": ("lunch", "box", "container"),
    "cert": ("certification", "certificate", "licence", "license"),
    "certification": ("licence", "license", "certificate", "isi"),
    "isi": ("certification", "mark", "licence"),
    "lab": ("laboratory", "testing"),
    "laboratory": ("lab", "testing"),
    "hallmark": ("hallmarking", "huid", "gold", "purity"),
    "hallmarking": ("hallmark", "huid", "purity", "assay"),
    "steel": ("stainless", "ss", "metal"),
    "stainless": ("steel", "ss", "corrosion"),
    "wire": ("cable", "conductor"),
    "cable": ("wire", "conductor"),
    "switch": ("accessory", "electrical"),
    "helmet": ("protective", "headgear"),
    "water": ("drinking", "potable"),
    "child": ("children", "kid", "school"),
    "children": ("child", "kid", "school"),
    "food": ("foodgrade", "contact", "edible"),
}


def stem(token: str) -> str:
    """Very small suffix stripper. Never shortens a token below 4 characters."""
    if token.isdigit() or len(token) <= 4:
        return token
    for suf in _SUFFIXES:
        if token.endswith(suf) and len(token) - len(suf) >= 4:
            return token[: -len(suf)]
    return token


def normalise_standard_number(raw: str) -> str:
    """Canonical form used as a join key everywhere: `IS 15111` / `IS 302-1`."""
    m = STANDARD_RE.search(raw or "")
    if not m:
        return (raw or "").strip().upper()
    number, part, _year = m.groups()
    return f"IS {number}" + (f"-{int(part)}" if part else "")


def extract_standard_numbers(text: str) -> list[str]:
    """All canonical IS designations mentioned in a piece of text, de-duplicated."""
    out: list[str] = []
    for m in STANDARD_RE.finditer(text or ""):
        number, part, _year = m.groups()
        key = f"IS {number}" + (f"-{int(part)}" if part else "")
        if key not in out:
            out.append(key)
    return out


def tokenize(text: str, *, expand: bool = False) -> list[str]:
    """Tokens for lexical matching.

    Designations become one token (``is302``) so `IS 302` cannot be diluted into the very
    common tokens `is` and `302`. With ``expand=True`` a small synonym set is appended --
    used for queries only, never when indexing, so document statistics stay honest.
    """
    text = text or ""
    tokens: list[str] = []

    spans: list[tuple[int, int]] = []
    for m in STANDARD_RE.finditer(text):
        number, part, year = m.groups()
        tokens.append(f"is{number}" + (f"p{int(part)}" if part else ""))
        tokens.append(f"is{number}")
        if year:
            tokens.append(year)
        spans.append(m.span())

    # Blank out designation spans so their digits are not re-tokenised as noise.
    if spans:
        chars = list(text)
        for start, end in spans:
            for i in range(start, end):
                chars[i] = " "
        text = "".join(chars)

    for raw in WORD_RE.findall(text.lower()):
        if raw in STOPWORDS or len(raw) < 2:
            continue
        tokens.append(stem(raw))

    if expand:
        for tok in list(tokens):
            for syn in SYNONYMS.get(tok, ()):  # noqa: PLC0206 - small fixed map
                tokens.append(stem(syn))

    return tokens


def clean_text(text: str) -> str:
    """Collapse the whitespace damage typical of PDF text extraction."""
    text = (text or "").replace("­", "")
    text = re.sub(r"[ \t\x0b\f\r]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"(?<=\w)-\n(?=\w)", "", text)  # de-hyphenate across line breaks
    return text.strip()
