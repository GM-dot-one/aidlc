"""LLM provider abstraction.

We keep the surface area narrow — one method, ``complete``, that takes a
system prompt + user message and returns a string. Structured outputs are
handled by callers via explicit JSON-in-response parsing (``extract_json``),
because every provider handles structured outputs slightly differently and
pinning to one tool-use schema would couple us to one vendor.
"""

from __future__ import annotations

from aidlc.config import LLMProvider, get_settings
from aidlc.llm.anthropic import AnthropicProvider
from aidlc.llm.base import LLMProvider as LLMProviderIface
from aidlc.llm.base import extract_json
from aidlc.llm.groq import GroqProvider

__all__ = ["LLMProviderIface", "extract_json", "get_llm"]


def get_llm() -> LLMProviderIface:
    """Factory that returns the configured provider.

    Resolved at call time (not import time) so tests can override settings
    without needing to reload the module.
    """
    settings = get_settings()
    if settings.aidlc_llm_provider is LLMProvider.anthropic:
        return AnthropicProvider(
            api_key=settings.require_anthropic_key().get_secret_value(),
            model=settings.anthropic_model,
        )
    if settings.aidlc_llm_provider is LLMProvider.groq:
        return GroqProvider(
            api_key=settings.require_groq_key().get_secret_value(),
            model=settings.groq_model,
        )
    raise ValueError(f"Unsupported LLM provider: {settings.aidlc_llm_provider}")
