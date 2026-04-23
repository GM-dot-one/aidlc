"""Stage 3b — Task → Code via a local coding agent (default: Claude Code).

Unlike ``task_to_code`` (one-shot LLM call + Contents-API commits), this
workflow prepares a dedicated clone of the target repo under
``AIDLC_WORKDIR/wp-{id}``, hands it to a ``CodingAgent``, then commits +
pushes whatever the agent produced and opens a draft PR.

Why two flavours:

- The API-only variant is cheap and deterministic — good for boilerplate.
- The Claude-Code variant lets the agent read the actual codebase, run
  tests, and iterate — needed for anything non-trivial.

Both paths end in the same state: a draft PR linked to an OpenProject
work package, a ``StatusSnapshot`` row, and a ``WorkflowRun`` entry so
``status_updates`` can track the PR to merge.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from aidlc import db, git_local
from aidlc.coding_agents import CodingAgent, CodingResult
from aidlc.git_host import GitHubClient, PullRequest
from aidlc.logging import get_logger
from aidlc.openproject import OpenProjectClient
from aidlc.prompts import render

log = get_logger(__name__)

_BRANCH_SAFE = re.compile(r"[^a-zA-Z0-9._/-]")


@dataclass
class TaskToCodeLocalResult:
    work_package_id: int
    branch: str
    pr_number: int
    pr_url: str
    changed_files: list[str]
    agent_summary: str


def _sanitize_branch(name: str) -> str:
    cleaned = _BRANCH_SAFE.sub("-", name).strip("-/")
    cleaned = re.sub(r"-+", "-", cleaned)
    cleaned = cleaned.replace("..", "-")
    if not cleaned:
        cleaned = "aidlc-change"
    return cleaned[:100]


def run_task_to_code_local(
    *,
    agent: CodingAgent,
    op: OpenProjectClient,
    gh: GitHubClient,
    work_package_id: int,
    repo: str,
    github_token: str,
    base_branch: str,
    workdir_root: Path,
    stack_hints: str = "(inspect the repo to determine the stack)",
    force: bool = False,
) -> TaskToCodeLocalResult:
    """Drive a single task work package through local code-gen + PR."""
    if not force and db.has_run("task_to_code_local", work_package_id):
        log.info("task_to_code_local.skip_already_run", wp=work_package_id)
        snapshot = db.get_snapshot(work_package_id)
        if snapshot is None or snapshot.pr_number is None:
            raise RuntimeError(
                f"work package {work_package_id} marked done but no PR recorded — use --force"
            )
        return TaskToCodeLocalResult(
            work_package_id=work_package_id,
            branch=f"aidlc/wp-{work_package_id}",
            pr_number=snapshot.pr_number,
            pr_url=f"https://github.com/{repo}/pull/{snapshot.pr_number}",
            changed_files=[],
            agent_summary="(skipped — already run)",
        )

    wp = op.get_work_package(work_package_id)
    log.info("task_to_code_local.start", wp=wp.id, subject=wp.subject, agent=agent.name)

    branch = _sanitize_branch(f"aidlc/wp-{wp.id}-{wp.subject.lower()}")

    # 1. Prepare a fresh clone on the feature branch.
    checkout = git_local.prepare_branch(
        workdir_root=workdir_root,
        repo=repo,
        token=github_token,
        base_branch=base_branch,
        branch=branch,
        task_id=wp.id,
    )

    # 2. Render the prompt and hand off to the coding agent.
    prompt = render(
        "task_to_code_local",
        subject=wp.subject,
        wp_id=str(wp.id),
        description=(wp.description_text or "").strip() or "(no description provided)",
        repo=repo,
        branch=branch,
        base_branch=base_branch,
        hints=stack_hints,
    )
    try:
        result: CodingResult = agent.implement(prompt=prompt, workdir=checkout.path)
    except Exception as exc:
        db.record_run(
            stage="task_to_code_local",
            work_package_id=wp.id,
            status="error",
            notes=f"coding agent failed: {exc}"[:500],
        )
        raise

    if not git_local.has_changes(checkout):
        db.record_run(
            stage="task_to_code_local",
            work_package_id=wp.id,
            status="error",
            notes="agent produced no file changes",
        )
        raise RuntimeError(
            f"Claude Code produced no file changes for WP #{wp.id}. Summary: {result.summary[:300]}"
        )

    files = git_local.changed_files(checkout)
    log.info("task_to_code_local.agent_done", files=len(files), turns=result.turns)

    # 3. Commit + push.
    commit_msg = f"feat(wp-{wp.id}): {wp.subject}\n\n{result.summary[:500]}"
    git_local.commit_all(checkout=checkout, message=commit_msg)
    git_local.push_branch(checkout)

    # 4. Open draft PR via the existing GitHubClient.
    pr_title = f"[WP-{wp.id}] {wp.subject}"
    pr_body = _build_pr_body(wp_id=wp.id, result=result, files=files, agent=agent.name)
    pr: PullRequest = gh.open_pull_request(
        title=pr_title, body=pr_body, head=branch, base=base_branch, draft=True
    )
    log.info("task_to_code_local.pr_opened", number=pr.number, url=pr.url)

    # 5. Link back to OpenProject.
    op.add_comment(
        wp.id,
        f"AI-DLC (via {agent.name}) opened a draft PR: [{pr.url}]({pr.url}). "
        f"Changed {len(files)} file(s). Agent summary:\n\n> {result.summary[:800]}",
    )

    # 6. Persist run + snapshot.
    db.upsert_snapshot(
        db.StatusSnapshot(
            work_package_id=wp.id,
            wp_status=wp.status_name,
            pr_number=pr.number,
            pr_state=pr.state,
            ci_conclusion=None,
        )
    )
    db.record_run(
        stage="task_to_code_local",
        work_package_id=wp.id,
        status="ok",
        pr_url=pr.url,
        branch_name=branch,
        notes=f"agent={agent.name} files={len(files)} turns={result.turns}",
    )
    return TaskToCodeLocalResult(
        work_package_id=wp.id,
        branch=branch,
        pr_number=pr.number,
        pr_url=pr.url,
        changed_files=files,
        agent_summary=result.summary,
    )


def _build_pr_body(*, wp_id: int, result: CodingResult, files: list[str], agent: str) -> str:
    file_list = "\n".join(f"- `{f}`" for f in files[:30])
    if len(files) > 30:
        file_list += f"\n- ... and {len(files) - 30} more"
    cost_line = f" | cost ≈ ${result.cost_usd:.3f}" if result.cost_usd is not None else ""
    turns_line = f" | turns: {result.turns}" if result.turns is not None else ""
    return (
        f"Opened by AI-DLC via **{agent}**{turns_line}{cost_line}.\n\n"
        f"## Agent summary\n\n{result.summary}\n\n"
        f"## Files changed ({len(files)})\n\n{file_list}\n\n"
        f"---\nLinked to OpenProject work package **#{wp_id}**.\n\n"
        "⚠️ Draft PR — please review carefully before merging. "
        "Tests (if any) were run by the agent but a human reviewer should still "
        "verify the change is correct and complete."
    )
