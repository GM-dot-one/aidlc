"""Unit tests for provider-agnostic helpers in aidlc.llm.base."""

from __future__ import annotations

import pytest

from aidlc.llm.base import extract_json


class TestExtractJson:
    def test_parses_bare_object(self) -> None:
        assert extract_json('{"a": 1}') == {"a": 1}

    def test_parses_bare_array(self) -> None:
        assert extract_json("[1, 2, 3]") == [1, 2, 3]

    def test_strips_json_fence(self) -> None:
        text = 'Here you go:\n```json\n{"ok": true}\n```\nThanks!'
        assert extract_json(text) == {"ok": True}

    def test_strips_plain_fence(self) -> None:
        text = "```\n[1,2]\n```"
        assert extract_json(text) == [1, 2]

    def test_handles_preamble(self) -> None:
        text = 'Sure! The spec is: {"summary": "x", "acceptance_criteria": []}'
        assert extract_json(text) == {"summary": "x", "acceptance_criteria": []}

    def test_prefers_first_valid_object(self) -> None:
        text = 'garbage {"a": 1} tail'
        assert extract_json(text) == {"a": 1}

    def test_raises_when_no_json(self) -> None:
        with pytest.raises(ValueError, match="No parseable JSON"):
            extract_json("just prose, no JSON here")

    def test_handles_nested_objects(self) -> None:
        text = 'pre {"a": {"b": {"c": [1,2,3]}}} post'
        assert extract_json(text) == {"a": {"b": {"c": [1, 2, 3]}}}
