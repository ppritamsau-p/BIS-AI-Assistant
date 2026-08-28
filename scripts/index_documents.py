#!/usr/bin/env python
"""Rebuild the index and report its health.

    python scripts/index_documents.py
    python scripts/index_documents.py --check      # exit non-zero if the index looks unusable
    python scripts/index_documents.py --probe      # run smoke queries against it

`--check` is intended for CI: an empty or clause-less index is a silent failure mode. The
assistant would still answer, just from thin evidence, so it is worth failing loudly.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.database.store import get_kb, reset_kb  # noqa: E402

PROBES = [
    ("I manufacture stainless steel lunch boxes for school children", "IS 14756"),
    ("Explain IS 302 in simple language", "IS 302-1"),
    ("What is hallmarking?", "IS 1417"),
    ("How do I bake a chocolate cake?", None),  # must retrieve nothing
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild and inspect the knowledge index")
    parser.add_argument("--check", action="store_true", help="Fail if the index looks unusable")
    parser.add_argument("--probe", action="store_true", help="Run smoke queries")
    args = parser.parse_args()

    reset_kb()
    kb = get_kb()
    stats = kb.stats()

    print("Index rebuilt.\n")
    for key in (
        "standards", "documents", "indexed_chunks", "certification_schemes",
        "laboratories", "hallmarking_topics", "failed_documents",
    ):
        print(f"  {key:24} {stats[key]}")
    print(f"  {'storage':24} {stats['storage_driver']}")
    print(f"  {'embeddings':24} {stats['embedding_provider']}")

    print("\n  chunks by document type:")
    for doc_type, count in sorted(stats["chunks_by_type"].items(), key=lambda kv: -kv[1]):
        print(f"    {count:5}  {doc_type}")

    if kb.failed_documents:
        print("\n  problems:")
        for entry in kb.failed_documents:
            print(f"    {entry['filename']}: {entry['reason']}")

    exit_code = 0

    if args.probe:
        print("\nSmoke queries:")
        for query, expected in PROBES:
            chunks = kb.retriever.retrieve(query, limit=3)
            found = [c.standard_number for c in chunks if c.standard_number]
            if expected is None:
                ok = not chunks
                detail = "no evidence (correct)" if ok else f"unexpectedly matched {found}"
            else:
                ok = expected in found
                detail = f"{found}" if found else "no evidence"
            print(f"  [{'PASS' if ok else 'FAIL'}] {query[:52]:<54} {detail}")
            if not ok:
                exit_code = 1

    if args.check:
        anchored = sum(1 for c in kb.chunks if c.clause or c.page)
        problems = []
        if stats["indexed_chunks"] == 0:
            problems.append("index is empty")
        if stats["standards"] == 0:
            problems.append("no standards loaded")
        if anchored == 0:
            problems.append("no chunk carries a clause or page anchor - citations would be useless")

        if problems:
            print("\nCHECK FAILED:")
            for problem in problems:
                print(f"  - {problem}")
            exit_code = 1
        else:
            print(f"\nCHECK PASSED ({anchored} chunks carry a citation anchor).")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
