"""Groq adapter.

Groq exposes an OpenAI-compatible chat completions API with a tight free
tier that is more than enough for this POC's idea→spec and spec→tasks
workflows. We use the official ``groq`` SDK so retries, streaming, and
future tool-use support come for free.

Keep this adapter thin — anything reusable across providers belongs in
``base.py``.
"""

from __future__ import annotations

from typing import Any

from groq import APIError, APIStatusError, Groq
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from aidlc.logging import get_logger

log = get_logger(__name__)

_RETRYABLE_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, APIStatusError):
        return exc.status_code in _RETRYABLE_STATUS
    return isinstance(exc, APIError)


class GroqProvider:
    """Implements ``llm.base.LLMProvider`` against the Groq chat API."""

    def __init__(self, *, api_key: str, model: str) -> None:
        self.model = model
        self._client: Any = Groq(api_key=api_key)

    @retry(
        reraise=True,
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=1, max=20),
        retry=retry_if_exception_type((APIError,)),
    )
    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> str:
        log.debug("groq.request", model=self.model, max_tokens=max_tokens)
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
        except APIStatusError as exc:
            if _is_retryable(exc):
                raise
            log.error("groq.non_retryable", status=exc.status_code)
            raise

        choices = getattr(response, "choices", None) or []
        if not choices:
            raise RuntimeError("Groq returned no choices")
        content = choices[0].message.content
        if not content:
            raise RuntimeError("Groq returned empty content")
        text: str = content
        return text
