#!/usr/bin/env python
"""Build the embedding index and persist the vectoriser artifacts.

    python scripts/create_embeddings.py
    python scripts/create_embeddings.py --provider sbert

The default offline embedder learns IDF weights from the corpus, so those weights must be
saved alongside the vectors: embedding a query with different IDF weights than the
documents were embedded with silently degrades retrieval. This script writes them to
`data/index/idf.json`.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> int:
    parser = argparse.ArgumentParser(description="Create embeddings for the indexed corpus")
    parser.add_argument("--provider", choices=["local", "sbert"], help="Override EMBEDDING_PROVIDER")
    parser.add_argument("--out", type=Path, default=Path("data/index"), help="Artifact directory")
    args = parser.parse_args()

    if args.provider:
        os.environ["EMBEDDING_PROVIDER"] = args.provider

    from backend.database.store import get_kb  # noqa: PLC0415 - after env override

    started = time.perf_counter()
    kb = get_kb()
    texts = [chunk.searchable_text() for chunk in kb.chunks]

    if not texts:
        print("No chunks to embed. Add documents under data/ first.")
        return 1

    print(f"Embedding {len(texts)} chunks with '{getattr(kb.embedder, 'name', 'unknown')}'…")
    vectors = kb.embedder.embed_documents(texts)
    elapsed = time.perf_counter() - started

    dim = len(vectors[0]) if vectors else 0
    print(f"Done in {elapsed:.2f}s — {len(vectors)} vectors of dimension {dim}.")

    if hasattr(kb.embedder, "save"):
        target = args.out / "idf.json"
        kb.embedder.save(target)
        print(f"Vectoriser weights written to {target}")
        print(
            "Keep this file with the vectors: queries must be embedded with the same IDF "
            "weights as the documents, or retrieval quality drops without any error."
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
