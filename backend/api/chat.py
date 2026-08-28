"""Conversational endpoint.

`POST /api/chat` returns the complete structured answer.
`POST /api/chat/stream` emits the same pipeline as Server-Sent Events so the UI can show
retrieval progressing. Both run identical logic; the stream simply reports the stages.
"""
from __future__ import annotations

import json
from typing import Iterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from backend.ai.composer import answer_question, answer_with_stages
from backend.api.deps import kb_dependency
from backend.database.store import KnowledgeBase
from backend.models.schemas import AssistantAnswer, ChatRequest

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=AssistantAnswer)
@router.post("/", response_model=AssistantAnswer, include_in_schema=False)
def chat(payload: ChatRequest, kb: KnowledgeBase = Depends(kb_dependency)) -> AssistantAnswer:
    return answer_question(kb, payload.message, language=payload.language)


@router.post("/stream")
def chat_stream(payload: ChatRequest, kb: KnowledgeBase = Depends(kb_dependency)) -> StreamingResponse:
    def event_source() -> Iterator[str]:
        for name, data in answer_with_stages(kb, payload.message, language=payload.language):
            yield f"event: {name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
