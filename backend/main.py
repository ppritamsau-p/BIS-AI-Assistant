"""FastAPI application entry point.

Run with:  uvicorn backend.main:app --reload --port 8000
"""
from __future__ import annotations

import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api import admin, chat, services_api, standards
from backend.config import settings
from backend.database.store import get_kb
from backend.models.schemas import HealthResponse

DESCRIPTION = """
AI-powered decision support for Indian Standards and BIS services.

Answers are produced by retrieval-augmented generation over an indexed BIS corpus.
The assistant does not answer technical questions from model memory: every technical claim
must be supported by retrieved evidence, and unsupported standard citations are stripped
before the response is returned.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    kb = get_kb()  # build the index once at startup rather than on first request
    stats = kb.stats()
    print(
        f"[startup] {stats['standards']} standards, {stats['indexed_chunks']} chunks "
        f"({stats['storage_driver']}, embeddings: {stats['embedding_provider']}, "
        f"LLM: {'claude' if settings.llm_enabled else 'extractive fallback'})"
    )
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description=DESCRIPTION,
    lifespan=lifespan,
    root_path="/api/backend" if __import__("os").getenv("VERCEL") else "",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------
# Rate limiting
# --------------------------------------------------------------------------
_hits: dict[str, deque[float]] = defaultdict(deque)
EXEMPT_PATHS = {"/api/health", "/docs", "/openapi.json", "/redoc"}


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    """Fixed-window-free sliding limiter, per client IP.

    In-process by design: a single-node prototype. Behind more than one worker, move this
    to Redis -- otherwise each worker enforces its own independent limit.
    """
    if request.url.path in EXEMPT_PATHS or request.method == "OPTIONS":
        return await call_next(request)

    client = request.client.host if request.client else "unknown"
    now = time.monotonic()
    window = _hits[client]
    while window and now - window[0] > 60:
        window.popleft()

    if len(window) >= settings.rate_limit_per_minute:
        retry_after = int(60 - (now - window[0])) + 1
        return JSONResponse(
            {"detail": "Rate limit exceeded. Please slow down."},
            status_code=429,
            headers={"Retry-After": str(retry_after)},
        )

    window.append(now)
    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(settings.rate_limit_per_minute)
    response.headers["X-RateLimit-Remaining"] = str(
        max(settings.rate_limit_per_minute - len(window), 0)
    )
    return response


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------
app.include_router(chat.router)
app.include_router(standards.router)
app.include_router(services_api.router)
app.include_router(admin.auth_router)
app.include_router(admin.router)


@app.get("/api/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    kb = get_kb()
    stats = kb.stats()
    return HealthResponse(
        status="ok",
        version=settings.version,
        llm_enabled=settings.llm_enabled,
        llm_model=settings.llm_model if settings.llm_enabled else None,
        storage=stats["storage_driver"],
        embedding_provider=stats["embedding_provider"],
        demo_mode=settings.demo_mode,
        indexed_chunks=stats["indexed_chunks"],
        standards=stats["standards"],
    )


@app.get("/api/meta", tags=["system"])
def meta() -> dict:
    """Everything the frontend needs to render honest provenance banners."""
    kb = get_kb()
    return {
        "app": settings.app_name,
        "version": settings.version,
        "demo_mode": settings.demo_mode,
        "demo_notice": (
            "DEMO DATA - Replace with authorized BIS data before production. "
            "The standards, schemes and laboratory records loaded here are illustrative "
            "records for the prototype, not an official BIS extract."
        ),
        "llm_enabled": settings.llm_enabled,
        "generator": (
            f"claude:{settings.llm_model}" if settings.llm_enabled
            else "extractive (no language model configured)"
        ),
        "languages": [
            {"code": "en", "label": "English"},
            {"code": "hi", "label": "हिंदी"},
            {"code": "bn", "label": "বাংলা"},
        ],
        **kb.stats(),
    }


@app.get("/", include_in_schema=False)
def root() -> dict:
    return {"service": settings.app_name, "docs": "/docs", "health": "/api/health"}
