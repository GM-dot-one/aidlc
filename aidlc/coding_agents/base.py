"""Coding-agent Protocol + result dataclass.

A ``CodingAgent`` is anything that can take a natural-language task
description plus a working directory and produce file changes. The workflow
asks the agent to ``implement(...)`` and then runs ``git status``/``git
diff`` to figure out what changed — we do not trust agents to self-report
their edits accurately.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable


@dataclass
class CodingResult:
    """Summary the workflow surfaces into PR body + WP comment."""

    summary: str
    raw_output: str = ""
    turns: int | None = None
    cost_usd: float | None = None


@runtime_checkable
class CodingAgent(Protocol):
    """Minimal surface every coding agent must implement."""

    name: str

    def implement(self, *, prompt: str, workdir: Path) -> CodingResult:
        """Run the agent against ``workdir``, returning a result summary.

        The workflow — not the agent — is responsible for detecting changed
        files (via ``git status``) and for the git add/commit/push dance.
        The agent's only job is to leave the working tree in a state where
        those changes are a reasonable implementation of the prompt.
        """
        ...
