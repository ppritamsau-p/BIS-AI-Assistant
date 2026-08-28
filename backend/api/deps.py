"""Shared FastAPI dependencies."""
from __future__ import annotations

from backend.database.store import KnowledgeBase, get_kb


def kb_dependency() -> KnowledgeBase:
    return get_kb()
