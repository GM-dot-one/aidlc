"""Anthropic Claude adapter.

Wraps the official ``anthropic`` SDK with retry + typed return. Keep this
adapter thin — anything reusable across providers belongs in ``base.py``.
"""

from __future__ import annotations

from typing import Any

from anthropic import Anthropic, APIError, APIStatusError
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


class AnthropicProvider:
    """Implements ``llm.base.LLMProvider``."""

    def __init__(self, *, api_key: str, model: str) -> None:
        self.model = model
        self._client: Any = Anthropic(api_key=api_key)

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
        log.debug("anthropic.request", model=self.model, max_tokens=max_tokens)
        try:
            response = self._client.messages.create(
                model=self.model,
                system=system,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": user}],
            )
        except APIStatusError as exc:
            if _is_retryable(exc):
                raise
            log.error("anthropic.non_retryable", status=exc.status_code)
            raise

        # Response is a list of content blocks; we only use text blocks.
        text_parts: list[str] = []
        for block in response.content:
            # SDK returns TextBlock | ToolUseBlock | etc; guard on attr presence
            if getattr(block, "type", None) == "text":
                text_parts.append(block.text)
        if not text_parts:
            raise RuntimeError("Anthropic returned no text content")
        return "\n".join(text_parts)
