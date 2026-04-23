"""Smoke-test the prompt loader so a missing template doesn't ship."""

from __future__ import annotations

import pytest

from aidlc.prompts import load, render


@pytest.mark.parametrize("name", ["idea_to_spec", "spec_to_tasks", "task_to_code"])
def test_all_templates_load(name: str) -> None:
    content = load(name)
    assert "$" in content, f"{name} should have at least one placeholder"
    assert "# Required output" in content


def test_render_substitutes_placeholders() -> None:
    out = render("idea_to_spec", subject="Hello", description="World")
    assert "Hello" in out
    assert "World" in out
    assert "$subject" not in out
    assert "$description" not in out


def test_render_is_forgiving_of_missing_placeholders() -> None:
    # safe_substitute keeps unknown placeholders intact rather than raising
    out = render("idea_to_spec", subject="Hello")
    assert "Hello" in out
    assert "$description" in out
