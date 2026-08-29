"""Central configuration. Everything is env-driven so the prototype runs with zero setup."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    """Runtime settings.

    The system is designed to degrade gracefully:
      * no DATABASE_URL  -> JSON-backed in-memory store (demo data)
      * no ANTHROPIC_API_KEY -> extractive composer (answers built only from retrieved text)
    Neither fallback is allowed to invent BIS content.
    """

    app_name: str = "BIS AI Intelligent Assistant"
    version: str = "0.1.0"

    # --- storage -----------------------------------------------------------
    database_url: str | None = os.getenv("DATABASE_URL") or None
    vector_backend: str = os.getenv("VECTOR_BACKEND", "auto")  # auto | pgvector | memory

    # --- llm ---------------------------------------------------------------
    anthropic_api_key: str | None = os.getenv("ANTHROPIC_API_KEY") or None
    llm_model: str = os.getenv("BIS_LLM_MODEL", "claude-opus-5")
    llm_effort: str | None = os.getenv("BIS_LLM_EFFORT") or None  # low|medium|high|xhigh|max
    llm_max_tokens: int = int(os.getenv("BIS_LLM_MAX_TOKENS", "16000"))

    # --- embeddings --------------------------------------------------------
    # local  -> deterministic offline TF-IDF vectoriser (demo grade, no network)
    # sbert  -> sentence-transformers, if installed
    embedding_provider: str = os.getenv("EMBEDDING_PROVIDER", "local")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    embedding_dim: int = int(os.getenv("EMBEDDING_DIM", "384"))

    # --- retrieval ---------------------------------------------------------
    retrieval_top_k: int = int(os.getenv("RETRIEVAL_TOP_K", "8"))
    retrieval_candidates: int = int(os.getenv("RETRIEVAL_CANDIDATES", "40"))
    min_evidence_score: float = float(os.getenv("MIN_EVIDENCE_SCORE", "0.08"))

    # Absolute admissibility floors. A rank-fused score cannot tell an on-topic query from
    # an off-topic one (see HybridRetriever._admissible), so these gate on the raw signals.
    # Tuned for the default offline embedder, whose cosine values are compressed. A real
    # sentence encoder (EMBEDDING_PROVIDER=sbert) produces much higher cosines -- raise
    # MIN_SEMANTIC_SCORE to roughly 0.45-0.55 when switching to one.
    min_lexical_score: float = float(os.getenv("MIN_LEXICAL_SCORE", "0.12"))
    min_semantic_score: float = float(os.getenv("MIN_SEMANTIC_SCORE", "0.30"))

    # --- security ----------------------------------------------------------
    jwt_secret: str = os.getenv("JWT_SECRET", "dev-only-secret-change-me")
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = int(os.getenv("JWT_EXPIRY_MINUTES", "720"))
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    cors_origins: list[str] = [
        o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()
    ]

    # --- content -----------------------------------------------------------
    demo_mode: bool = _bool("DEMO_MODE", True)

    @property
    def default_upload_dir(self) -> Path:
        if os.getenv("VERCEL"):
            import tempfile
            return Path(tempfile.gettempdir()) / "uploads"
        return BASE_DIR / "data" / "uploads"

    @property
    def _upload_dir_path(self) -> Path:
        return Path(os.getenv("UPLOAD_DIR", str(self.default_upload_dir)))

    @property
    def upload_dir(self) -> Path:
        return self._upload_dir_path

    @property
    def llm_enabled(self) -> bool:
        return bool(self.anthropic_api_key)

    @property
    def use_postgres(self) -> bool:
        return bool(self.database_url) and self.vector_backend in {"auto", "pgvector"}


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    try:
        s.upload_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass  # Read-only file system on Vercel/Serverless
    return s


settings = get_settings()
