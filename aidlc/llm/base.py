"""Provider-agnostic LLM interface."""

from __future__ import annotations

import json
import re
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    """Minimal surface every provider must implement."""

    model: str

    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> str:
        """Return the assistant's text response for a single-turn exchange."""
        ...


_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", re.DOTALL)


def extract_json(text: str) -> Any:
    """Pull a JSON object/array out of an LLM response.

    LLMs love to wrap JSON in ``` fences or add a preamble like
    "Here's the spec:". We try three strategies in order:

    1. Strict parse the whole string.
    2. Find a ```json fenced block.
    3. Find the first balanced ``{...}`` or ``[...]`` substring and parse it.

    Raises ``ValueError`` if nothing parseable is found, so callers can
    surface the raw output for debugging instead of silently failing.
    """
    text = text.strip()

    # 1. Whole-string parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. Fenced block
    match = _FENCE_RE.search(text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # 3. First balanced object/array
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        if start == -1:
            continue
        depth = 0
        for i in range(start, len(text)):
            c = text[i]
            if c == opener:
                depth += 1
            elif c == closer:
                depth -= 1
                if depth == 0:
                    candidate = text[start : i + 1]
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        break  # try the next opener

    raise ValueError(f"No parseable JSON found in LLM output:\n{text[:500]}")
