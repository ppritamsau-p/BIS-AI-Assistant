"""Anthropic Claude client wrapper.

All model access goes through here so that:
  * the API key never leaves the server,
  * every call carries the guardrail system prompt,
  * and a missing key or a failed call degrades to the extractive composer instead of
    surfacing an error to the user.

Requests use `messages.stream(...)` + `get_final_message()` rather than a plain create:
evidence blocks make these prompts long, and streaming avoids HTTP timeouts on the larger
ones without changing how the result is consumed.
"""
from __future__ import annotations

import json
import re
from typing import Any

from backend.config import settings
from backend.ai.prompts import (
    PRODUCT_EXTRACTION_PROMPT,
    SYSTEM_PROMPT,
    TRANSLATION_PROMPT,
)

JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)

LANGUAGE_NAMES = {"en": "English", "hi": "Hindi", "bn": "Bengali"}


class LLMUnavailable(RuntimeError):
    """Raised when no model is configured or the call could not be completed."""


class ClaudeClient:
    def __init__(self) -> None:
        self._client = None
        self.model = settings.llm_model
        self.available = False
        if not settings.llm_enabled:
            return
        try:
            import anthropic  # noqa: PLC0415

            self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
            self._anthropic = anthropic
            self.available = True
        except ImportError:
            print("[llm] `anthropic` package not installed; using the extractive composer")
        except Exception as exc:  # pragma: no cover
            print(f"[llm] client init failed ({exc}); using the extractive composer")

    # ------------------------------------------------------------------
    def _request_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": settings.llm_max_tokens,
        }
        # Adaptive thinking is the default on this model family; effort is only sent when
        # explicitly configured, so we inherit the model's own default otherwise.
        if settings.llm_effort:
            kwargs["output_config"] = {"effort": settings.llm_effort}
        return kwargs

    def complete(self, user_turn: str, *, system: str = SYSTEM_PROMPT) -> str:
        """Single-turn completion returning the concatenated text blocks."""
        if not self.available or self._client is None:
            raise LLMUnavailable("no model configured")

        anthropic = self._anthropic
        try:
            with self._client.messages.stream(
                system=system,
                messages=[{"role": "user", "content": user_turn}],
                **self._request_kwargs(),
            ) as stream:
                message = stream.get_final_message()
        except anthropic.NotFoundError as exc:
            raise LLMUnavailable(f"model '{self.model}' not available: {exc}") from exc
        except anthropic.AuthenticationError as exc:
            raise LLMUnavailable("invalid ANTHROPIC_API_KEY") from exc
        except anthropic.RateLimitError as exc:
            raise LLMUnavailable("rate limited by the Claude API") from exc
        except anthropic.APIStatusError as exc:
            raise LLMUnavailable(f"Claude API error {exc.status_code}") from exc
        except anthropic.APIConnectionError as exc:
            raise LLMUnavailable(f"could not reach the Claude API: {exc}") from exc

        if getattr(message, "stop_reason", None) == "refusal":
            raise LLMUnavailable("the model declined to answer this request")

        return "".join(b.text for b in message.content if b.type == "text").strip()

    # ------------------------------------------------------------------
    def complete_json(self, user_turn: str, *, system: str = SYSTEM_PROMPT) -> dict[str, Any]:
        """Completion parsed as a JSON object, tolerant of fenced or padded output."""
        raw = self.complete(user_turn, system=system)
        return parse_json_object(raw)

    def translate(self, text: str, target_language: str) -> str:
        target = LANGUAGE_NAMES.get(target_language, "English")
        return self.complete(text, system=TRANSLATION_PROMPT.format(target=target))

    def enrich_product(self, description: str) -> dict[str, Any]:
        """Ask the model for a product profile. Never asked for standards or requirements."""
        turn = (
            f"{description}\n\nReturn JSON with keys: product, category, materials (list), "
            "intended_use, industry, target_user, characteristics (list)."
        )
        return self.complete_json(turn, system=PRODUCT_EXTRACTION_PROMPT)


def parse_json_object(raw: str) -> dict[str, Any]:
    """Extract the first JSON object from model output."""
    raw = (raw or "").strip()
    if not raw:
        raise LLMUnavailable("empty model response")

    fenced = JSON_BLOCK_RE.search(raw)
    if fenced:
        raw = fenced.group(1)

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start == -1 or end <= start:
            raise LLMUnavailable("model response was not JSON") from None
        try:
            parsed = json.loads(raw[start : end + 1])
        except json.JSONDecodeError as exc:
            raise LLMUnavailable(f"model response was not valid JSON: {exc}") from exc

    if not isinstance(parsed, dict):
        raise LLMUnavailable("model response was not a JSON object")
    return parsed


_client: ClaudeClient | None = None


def get_llm() -> ClaudeClient:
    global _client  # noqa: PLW0603
    if _client is None:
        _client = ClaudeClient()
    return _client
