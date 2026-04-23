"""Claude Code adapter — shells out to the `claude` CLI.

The Claude Code CLI in ``-p`` (print) mode runs the agent non-interactively:
it takes a prompt on argv, executes the agent loop in the current working
directory, and exits when the agent decides the task is done (or
``--max-turns`` is hit). Combined with ``--permission-mode
bypassPermissions`` this is a fully headless runner suitable for CI /
batch pipelines.

We keep this adapter dumb: build argv, run subprocess, parse stdout. The
workflow owns git, the PR, and the OpenProject update.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from aidlc.coding_agents.base import CodingResult
from aidlc.logging import get_logger

log = get_logger(__name__)


class ClaudeCodeAgent:
    """Implements ``coding_agents.base.CodingAgent`` via the `claude` CLI."""

    name = "claude-code"

    def __init__(
        self,
        *,
        bin_path: str = "claude",
        permission_mode: str = "bypassPermissions",
        max_turns: int = 40,
        timeout_s: int = 1800,
    ) -> None:
        self.bin_path = bin_path
        self.permission_mode = permission_mode
        self.max_turns = max_turns
        self.timeout_s = timeout_s

    def implement(self, *, prompt: str, workdir: Path) -> CodingResult:
        if not workdir.exists():
            raise FileNotFoundError(f"workdir does not exist: {workdir}")

        cmd = [
            self.bin_path,
            "-p",
            prompt,
            "--permission-mode",
            self.permission_mode,
            "--output-format",
            "json",
            "--max-turns",
            str(self.max_turns),
        ]
        log.info(
            "claude_code.start",
            workdir=str(workdir),
            permission_mode=self.permission_mode,
            max_turns=self.max_turns,
        )
        try:
            proc = subprocess.run(
                cmd,
                cwd=workdir,
                capture_output=True,
                text=True,
                timeout=self.timeout_s,
                check=False,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"`{self.bin_path}` not found on PATH — install Claude Code "
                "(https://docs.claude.com/en/docs/claude-code/quickstart) or "
                "set AIDLC_CLAUDE_CODE_BIN to the full path."
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                f"claude code timed out after {self.timeout_s}s — consider raising "
                "AIDLC_CLAUDE_CODE_TIMEOUT_S or simplifying the task prompt."
            ) from exc

        if proc.returncode != 0:
            raise RuntimeError(f"claude exited {proc.returncode}\nstderr:\n{proc.stderr[:2000]}")

        payload = _parse_json_output(proc.stdout)
        summary = str(payload.get("result") or payload.get("response") or "").strip() or (
            "(claude code returned no summary)"
        )
        if payload.get("is_error"):
            raise RuntimeError(f"claude reported error: {summary[:500]}")

        turns = payload.get("num_turns")
        cost = payload.get("total_cost_usd")

        log.info("claude_code.done", turns=turns, cost_usd=cost)
        return CodingResult(
            summary=summary,
            raw_output=proc.stdout,
            turns=int(turns) if isinstance(turns, (int, float)) else None,
            cost_usd=float(cost) if isinstance(cost, (int, float)) else None,
        )


def _parse_json_output(stdout: str) -> dict[str, Any]:
    """Claude emits one JSON object per run in --output-format=json.

    Be defensive: some versions include a trailing newline or prepend a
    progress line. We try the last non-empty line first, then the whole
    stdout, then give up with an empty dict (caller will surface raw).
    """
    lines = [ln for ln in stdout.splitlines() if ln.strip()]
    for candidate in (lines[-1] if lines else "", stdout):
        try:
            data: Any = json.loads(candidate)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            continue
    return {}
