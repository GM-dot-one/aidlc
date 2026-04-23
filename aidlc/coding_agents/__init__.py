"""Pluggable code-generation agents.

We isolate the code-writing step behind a small Protocol so the workflow
doesn't care whether files were authored by Claude Code, Aider, Cursor CLI,
or a future home-grown agent. Default implementation shells out to the
`claude` CLI in non-interactive (`-p`) mode.
"""

from __future__ import annotations

from aidlc.coding_agents.base import CodingAgent, CodingResult
from aidlc.coding_agents.claude_code import ClaudeCodeAgent

__all__ = ["ClaudeCodeAgent", "CodingAgent", "CodingResult"]
