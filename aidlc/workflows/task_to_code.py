"""Stage 3 — Task → Code / PR.

Given a child task, ask the LLM for a starter code change, create a branch
on the target GitHub repo, commit the files, and open a PR. We then link
the PR back to the OpenProject work package via a comment + link the
work-package id in the PR body for bidirectional traceability.

We deliberately keep the code surface small: this is a scaffold + failing
test generator, not a full autonomous coding agent. For a real AI-DLC you'd
plug this into Claude Code or a codegen agent that can actually run tests
against the target repo.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from aidlc import db
from aidlc.git_host import GitHubClient, PullRequest
from aidlc.llm import LLMProviderIface, extract_json
from aidlc.logging import get_logger
from aidlc.openproject import OpenProjectClient
from aidlc.prompts import render

log = get_logger(__name__)

_BRANCH_SAFE = re.compile(r"[^a-zA-Z0-9._/-]")


@dataclass
class TaskToCodeResult:
    work_package_id: int
    branch: str
    pr_number: int
    pr_url: str


def _sanitize_branch(name: str) -> str:
    """Git ref rules: no spaces, no `..`, no leading `/`, ≤100 chars."""
    cleaned = _BRANCH_SAFE.sub("-", name).strip("-/")
    cleaned = re.sub(r"-+", "-", cleaned)
    cleaned = cleaned.replace("..", "-")
    if not cleaned:
        cleaned = "aidlc-change"
    return cleaned[:100]


def run_task_to_code(
    *,
    llm: LLMProviderIface,
    op: OpenProjectClient,
    gh: GitHubClient,
    work_package_id: int,
    repo: str,
    base_branch: str,
    stack_hints: str = "Python / FastAPI / pytest (adjust if your repo differs)",
    force: bool = False,
) -> TaskToCodeResult:
    if not force and db.has_run("task_to_code", work_package_id):
        log.info("task_to_code.skip_already_run", wp=work_package_id)
        snapshot = db.get_snapshot(work_package_id)
        if snapshot is None or snapshot.pr_number is None:
            raise RuntimeError(
                f"work package {work_package_id} marked done but no PR recorded — use --force"
            )
        # Rehydrate what we can for the caller.
        return TaskToCodeResult(
            work_package_id=work_package_id,
            branch=f"aidlc/wp-{work_package_id}",
            pr_number=snapshot.pr_number,
            pr_url=f"https://github.com/{repo}/pull/{snapshot.pr_number}",
        )

    wp = op.get_work_package(work_package_id)
    log.info("task_to_code.start", wp=wp.id, subject=wp.subject)

    prompt = render(
        "task_to_code",
        subject=wp.subject,
        description=(wp.description_text or "").strip() or "(no description provided)",
        repo=repo,
        base_branch=base_branch,
        hints=stack_hints,
    )
    raw = llm.complete(
        system="You produce small, review-ready PR scaffolds.",
        user=prompt,
        max_tokens=4000,
    )
    try:
        plan: dict[str, Any] = extract_json(raw)
    except ValueError:
        db.record_run(
            stage="task_to_code",
            work_package_id=wp.id,
            status="error",
            notes=f"Unparseable LLM output:\n{raw[:1000]}",
        )
        raise

    branch = _sanitize_branch(str(plan.get("branch_name") or f"aidlc/wp-{wp.id}"))
    if not branch.startswith("aidlc/"):
        branch = f"aidlc/{branch}"

    files = plan.get("files") or []
    if not files:
        raise ValueError("LLM returned a plan with no files")
    if len(files) > 10:
        raise ValueError(f"Plan has {len(files)} files; refusing (>10)")

    commit_message = str(plan.get("commit_message") or f"chore: scaffold {wp.subject}")
    pr_title = str(plan.get("pr_title") or f"[WP-{wp.id}] {wp.subject}")
    pr_body = str(plan.get("pr_body") or "Scaffolded by AI-DLC.")
    pr_body += f"\n\n---\nLinked to OpenProject work package **#{wp.id}**."

    # Create the branch off base_branch
    base_sha = gh.get_branch_sha(base_branch)
    gh.create_branch(new_branch=branch, from_sha=base_sha)
    log.info("task_to_code.branch_created", branch=branch, base_sha=base_sha[:8])

    for f in files:
        path = str(f["path"])
        content = str(f["content"])
        gh.commit_file(
            branch=branch,
            path=path,
            content=content,
            message=f"{commit_message} ({path})",
        )
        log.info("task_to_code.file_committed", path=path)

    pr: PullRequest = gh.open_pull_request(
        title=pr_title, body=pr_body, head=branch, base=base_branch, draft=True
    )
    log.info("task_to_code.pr_opened", number=pr.number, url=pr.url)

    op.add_comment(
        wp.id,
        f"AI-DLC opened a draft PR: [{pr.url}]({pr.url}). "
        "Please review the scaffold — it is deliberately minimal and marks "
        "outstanding acceptance criteria in the PR body.",
    )

    # Store snapshot so status_updates can pick this up.
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
        stage="task_to_code",
        work_package_id=wp.id,
        status="ok",
        pr_url=pr.url,
        branch_name=branch,
        notes=json.dumps({"files": [f["path"] for f in files]})[:500],
    )
    return TaskToCodeResult(
        work_package_id=wp.id,
        branch=branch,
        pr_number=pr.number,
        pr_url=pr.url,
    )
