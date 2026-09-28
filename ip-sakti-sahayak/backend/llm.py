"""Optional compatible API client for planning, checked synthesis and translation.

Provider errors become LLMError so callers can use the local source passages.
No specific model or hosted gateway is assumed.
"""
from __future__ import annotations
import httpx
from .config import settings


class LLMError(RuntimeError):
    pass


def _endpoint(base: str, suffix: str) -> str:
    base = base.rstrip("/")
    if base.endswith(suffix.rstrip("/")):
        return base
    if base.endswith("/v1") and suffix.startswith("/v1/"):
        return base + suffix[3:]
    return base + suffix


def chat(system: str, user: str, *, temperature: float = 0.0, max_tokens: int | None = None) -> str:
    """Single-turn completion. Raises LLMError on any failure (callers fall back)."""
    if not settings.llm_enabled:
        raise LLMError("LLM not configured")
    max_tokens = max_tokens or settings.llm_max_tokens
    try:
        if settings.llm_provider == "anthropic":
            url = _endpoint(settings.llm_base_url or "https://api.anthropic.com", "/v1/messages")
            headers = {
                "x-api-key": settings.llm_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
                "User-Agent": settings.llm_user_agent,
            }
            body = {
                "model": settings.llm_model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            }
            with httpx.Client(timeout=settings.llm_timeout) as c:
                r = c.post(url, headers=headers, json=body)
                r.raise_for_status()
                data = r.json()
            parts = data.get("content", [])
            text = "".join(p.get("text", "") for p in parts if p.get("type") == "text")
            if not text:
                raise LLMError("empty anthropic response")
            return text.strip()

        if settings.llm_provider == "openai":
            url = _endpoint(settings.llm_base_url or "https://api.openai.com", "/v1/chat/completions")
            headers = {
                "Authorization": f"Bearer {settings.llm_api_key}",
                "content-type": "application/json",
                "User-Agent": settings.llm_user_agent,
            }
            body = {
                "model": settings.llm_model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            }
            with httpx.Client(timeout=settings.llm_timeout) as c:
                r = c.post(url, headers=headers, json=body)
                r.raise_for_status()
                data = r.json()
            return data["choices"][0]["message"]["content"].strip()

        raise LLMError(f"unknown provider {settings.llm_provider}")
    except httpx.HTTPError as e:
        raise LLMError(f"http error: {e}") from e
    except (KeyError, IndexError, ValueError, TypeError, AttributeError) as e:
        raise LLMError(f"bad response: {e}") from e


def available() -> bool:
    return settings.llm_enabled
