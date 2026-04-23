"""Batch driver — run ``task_to_code_local`` across all children of a parent WP.

Cumulative branching: all tasks share ONE workdir and ONE branch. Each task
builds on top of the previous task's committed code, so later agents see
what earlier agents actually built. One PR is opened at the end containing
all commits.

This solves the coherence problem where independent per-task branches
produce conflicting code that doesn't integrate (e.g. splitting an SPA
into "add routing" / "add state" / "add display" tasks that each assume
different interfaces).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from aidlc import db, git_local
from aidlc.coding_agents import CodingAgent
from aidlc.git_host import GitHubClient, PullRequest
from aidlc.logging import get_logger
from aidlc.openproject import OpenProjectClient
from aidlc.openproject.models import WorkPackage
from aidlc.workflows.task_to_code_local import (
    TaskToCodeLocalResult,
    _sanitize_branch,
    run_task_to_code_local,
)

log = get_logger(__name__)


@dataclass
class CodeAllLocalResult:
    parent_work_package_id: int
    pr_number: int = 0
    pr_url: str = ""
    successes: list[TaskToCodeLocalResult] = field(default_factory=list)
    failures: list[tuple[int, str]] = field(default_factory=list)  # (wp_id, error)


def _get_shared_context(parent_wp_id: int) -> str:
    """Retrieve the shared_context stored by spec_to_tasks, if any."""
    notes_raw = db.get_run_notes("spec_to_tasks", parent_wp_id)
    if not notes_raw:
        return ""
    try:
        notes = json.loads(notes_raw)
        return str(notes.get("shared_context", ""))
    except (json.JSONDecodeError, TypeError):
        return ""


def _build_sibling_tasks_text(children: list[WorkPackage]) -> str:
    lines = []
    for i, child in enumerate(children, 1):
        desc_preview = (child.description_text or "").strip()[:200]
        lines.append(f"{i}. **{child.subject}** (WP #{child.id})\n   {desc_preview}")
    return "\n".join(lines)


def _build_prior_work_summary(completed: list[TaskToCodeLocalResult]) -> str:
    if not completed:
        return ""
    lines = ["The following tasks have already been implemented in this branch:\n"]
    for r in completed:
        lines.append(f"- **{r.agent_summary[:200]}** ({len(r.changed_files)} files changed)")
    return "\n".join(lines)


def _build_parent_spec_text(parent: WorkPackage) -> str:
    desc = (parent.description_text or "").strip()
    if not desc:
        return f"**{parent.subject}** — (no spec available)"
    return f"**{parent.subject}**\n\n{desc[:2000]}"


def run_code_all_local(
    *,
    agent: CodingAgent,
    op: OpenProjectClient,
    gh: GitHubClient,
    parent_work_package_id: int,
    repo: str,
    github_token: str,
    base_branch: str,
    workdir_root: Path,
    stack_hints: str = "(inspect the repo to determine the stack)",
    force: bool = False,
    project_identifier: str | None = None,
) -> CodeAllLocalResult:
    """Run code-gen for every child task using cumulative branching.

    All tasks share one workdir and one branch. Each task's agent sees the
    code from all previous tasks. One PR is opened at the end.
    """
    parent = op.get_work_package(parent_work_package_id)
    project = project_identifier or parent.project_identifier
    if project is None:
        raise RuntimeError(
            f"cannot determine project for parent WP {parent_work_package_id}; "
            "pass project_identifier explicitly"
        )

    all_wps = op.list_work_packages(project_identifier=project, page_size=200)
    children: list[WorkPackage] = sorted(
        (wp for wp in all_wps if wp.parent_id == parent_work_package_id),
        key=lambda w: w.id,
    )
    if not children:
        raise RuntimeError(
            f"WP #{parent_work_package_id} has no child tasks — run `aidlc decompose` first"
        )
    log.info("code_all_local.start", parent=parent_work_package_id, children=len(children))

    # Build context that will be shared across all tasks.
    shared_context = _get_shared_context(parent_work_package_id)
    sibling_tasks_text = _build_sibling_tasks_text(children)
    parent_spec_text = _build_parent_spec_text(parent)

    # Prepare ONE cumulative branch for all tasks.
    branch = _sanitize_branch(f"aidlc/wp-{parent_work_package_id}-{parent.subject.lower()}")
    checkout = git_local.prepare_branch(
        workdir_root=workdir_root,
        repo=repo,
        token=github_token,
        base_branch=base_branch,
        branch=branch,
        task_id=parent_work_package_id,
    )

    result = CodeAllLocalResult(parent_work_package_id=parent_work_package_id)

    for child in children:
        prior_work = _build_prior_work_summary(result.successes)
        try:
            r = run_task_to_code_local(
                agent=agent,
                op=op,
                gh=gh,
                work_package_id=child.id,
                repo=repo,
                github_token=github_token,
                base_branch=base_branch,
                workdir_root=workdir_root,
                stack_hints=stack_hints,
                force=force,
                parent_subject=parent.subject,
                parent_spec=parent_spec_text,
                sibling_tasks=sibling_tasks_text,
                shared_context=shared_context,
                prior_work_summary=prior_work,
                checkout_override=checkout,
                skip_push_and_pr=True,
            )
            result.successes.append(r)
            log.info("code_all_local.child_ok", wp=child.id, files=len(r.changed_files))
        except Exception as exc:
            log.error("code_all_local.child_failed", wp=child.id, error=str(exc))
            result.failures.append((child.id, str(exc)[:500]))

    if not result.successes:
        log.warning("code_all_local.no_successes", parent=parent_work_package_id)
        return result

    # Push the cumulative branch and open ONE PR.
    git_local.push_branch(checkout)

    all_files = []
    summaries = []
    for r in result.successes:
        all_files.extend(r.changed_files)
        summaries.append(f"### WP #{r.work_package_id}\n{r.agent_summary}")

    child_ids = [r.work_package_id for r in result.successes]
    pr_title = f"[WP-{parent_work_package_id}] {parent.subject}"
    pr_body = (
        f"Opened by AI-DLC via **{agent.name}** — cumulative PR for "
        f"{len(result.successes)} task(s).\n\n"
        f"## Task summaries\n\n" + "\n\n".join(summaries) + "\n\n"
        f"## Files changed ({len(set(all_files))})\n\n"
        + "\n".join(f"- `{f}`" for f in sorted(set(all_files))[:40])
        + ("\n- ... and more" if len(set(all_files)) > 40 else "")
        + f"\n\n---\nLinked to OpenProject parent WP **#{parent_work_package_id}**, "
        f"child tasks: {child_ids}\n\n"
        "⚠️ Draft PR — please review carefully before merging."
    )

    pr: PullRequest = gh.open_pull_request(
        title=pr_title, body=pr_body, head=branch, base=base_branch, draft=True
    )
    result.pr_number = pr.number
    result.pr_url = pr.url
    log.info("code_all_local.pr_opened", number=pr.number, url=pr.url)

    # Link PR back to all child WPs and parent.
    op.add_comment(
        parent_work_package_id,
        f"AI-DLC opened a cumulative PR for all child tasks: [{pr.url}]({pr.url}). "
        f"{len(result.successes)} tasks coded, {len(result.failures)} failed.",
    )
    for r in result.successes:
        db.upsert_snapshot(
            db.StatusSnapshot(
                work_package_id=r.work_package_id,
                pr_number=pr.number,
                pr_state=pr.state,
                ci_conclusion=None,
            )
        )

    return result
