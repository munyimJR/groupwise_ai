"""LLM access (Anthropic Claude). The LLM only turns *computed* facts into language.

If no API key is configured, the API errors, times out or declines, callers receive
LLMUnavailable and fall back to deterministic templates — the rest of the product is unaffected.
"""
from __future__ import annotations

import logging
import threading
import time

import anthropic

from ..config import get_settings

log = logging.getLogger("groupwise.llm")

# Models that accept the server-side refusal fallback ("default" routing).
_FALLBACK_MODELS = {"claude-opus-5-5", "claude-opus-5", "claude-fable-5-1", "claude-sonnet-5-5"}
_COOLDOWN_SECONDS = 60


class LLMUnavailable(RuntimeError):
    pass


_state = {"disabled_until": 0.0, "last_error": None}
_lock = threading.Lock()
_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    settings = get_settings()
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key, timeout=settings.llm_timeout_seconds,
                                      max_retries=1)
    return _client


def llm_status() -> dict:
    settings = get_settings()
    if not settings.llm_enabled:
        return {"available": False, "model": settings.llm_model, "reason": "disabled by configuration"}
    if not settings.anthropic_api_key:
        return {"available": False, "model": settings.llm_model, "reason": "no API key configured"}
    if time.time() < _state["disabled_until"]:
        return {"available": False, "model": settings.llm_model, "reason": f"temporarily unavailable ({_state['last_error']})"}
    return {"available": True, "model": settings.llm_model, "reason": None}


def _trip(reason: str) -> None:
    with _lock:
        _state["disabled_until"] = time.time() + _COOLDOWN_SECONDS
        _state["last_error"] = reason


def generate(system: str, user: str, max_tokens: int = 1200) -> str:
    status = llm_status()
    if not status["available"]:
        raise LLMUnavailable(status["reason"])
    settings = get_settings()
    client = _get_client()
    kwargs = dict(model=settings.llm_model, max_tokens=max_tokens, system=system,
                  messages=[{"role": "user", "content": user}], output_config={"effort": settings.llm_effort})
    try:
        if settings.llm_model in _FALLBACK_MODELS:
            try:
                response = client.beta.messages.create(betas=["server-side-fallback-2026-07-01"], fallbacks="default",
                                                       **kwargs)
            except anthropic.BadRequestError:
                response = client.messages.create(**kwargs)  # fallback parameter not accepted → plain request
        else:
            response = client.messages.create(**kwargs)
    except anthropic.AuthenticationError as exc:
        _trip("authentication failed")
        raise LLMUnavailable("authentication failed") from exc
    except anthropic.RateLimitError as exc:
        _trip("rate limited")
        raise LLMUnavailable("rate limited") from exc
    except anthropic.APIStatusError as exc:
        if exc.status_code >= 500:
            _trip(f"server error {exc.status_code}")
        raise LLMUnavailable(f"API error {exc.status_code}") from exc
    except anthropic.APIConnectionError as exc:  # includes timeouts
        _trip("connection error")
        raise LLMUnavailable("connection error") from exc

    if response.stop_reason == "refusal":
        raise LLMUnavailable("the model declined to answer")
    text = "".join(block.text for block in response.content if block.type == "text").strip()
    if not text:
        raise LLMUnavailable("empty response")
    return text
