#!/usr/bin/env python
"""Ingest BIS documents into the knowledge base.

    python scripts/ingest_documents.py path/to/IS-14756.pdf
    python scripts/ingest_documents.py data/standards --recursive
    python scripts/ingest_documents.py corpus/ --recursive --dry-run

Extracts text (with OCR for scanned pages when the toolchain is available), chunks it
clause-by-clause, and reports what was indexed. Run from the project root.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.rag.ingest import build_chunk_records, extract_document  # noqa: E402
from backend.retrieval.text import normalise_standard_number  # noqa: E402

SUPPORTED = {".pdf", ".txt", ".md"}


def collect(target: Path, recursive: bool) -> list[Path]:
    if target.is_file():
        return [target]
    pattern = "**/*" if recursive else "*"
    return sorted(p for p in target.glob(pattern) if p.is_file() and p.suffix.lower() in SUPPORTED)


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest BIS documents")
    parser.add_argument("path", type=Path, help="File or directory to ingest")
    parser.add_argument("--recursive", action="store_true", help="Recurse into subdirectories")
    parser.add_argument("--no-ocr", action="store_true", help="Skip OCR for scanned pages")
    parser.add_argument("--dry-run", action="store_true", help="Report without writing an index")
    parser.add_argument("--standard", help="Force the standard number for every document")
    args = parser.parse_args()

    if not args.path.exists():
        print(f"error: {args.path} does not exist", file=sys.stderr)
        return 1

    files = collect(args.path, args.recursive)
    if not files:
        print(f"No supported documents found in {args.path} (looked for {', '.join(SUPPORTED)})")
        return 1

    total_chunks = 0
    failures = 0

    for path in files:
        try:
            doc = extract_document(path, enable_ocr=not args.no_ocr)
        except Exception as exc:
            print(f"  FAILED  {path.name}: {exc}")
            failures += 1
            continue

        number = normalise_standard_number(args.standard) if args.standard else doc.standard_number
        records = build_chunk_records(doc, standard_number=number)
        total_chunks += len(records)

        clauses = sum(1 for r in records if r["clause"])
        print(
            f"  OK      {path.name}: {doc.pages} page(s), {len(records)} chunk(s), "
            f"{clauses} with a clause anchor, standard={number or 'unidentified'}"
        )
        for warning in doc.warnings:
            print(f"          warning: {warning}")
        if doc.ocr_pages:
            print(f"          OCR applied to pages: {doc.ocr_pages}")

    print(f"\n{len(files) - failures}/{len(files)} document(s) processed, {total_chunks} chunks total.")

    if args.dry_run:
        print("Dry run - nothing was indexed.")
        return 0

    print(
        "\nThe running backend indexes data/ at startup. To make these documents part of the "
        "knowledge base, place them under data/ and restart the API (or upload them through "
        "the admin console, which indexes immediately)."
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
