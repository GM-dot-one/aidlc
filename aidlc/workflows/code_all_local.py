"""Batch driver — run ``task_to_code_local`` across all children of a parent WP.

Sequential, not parallel: Claude Code sessions are token-heavy and we want
per-task PRs to stay atomic. A failed task is logged but does not abort
the batch — the operator can re-run just the failures with ``--force``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from aidlc.coding_agents import CodingAgent
from aidlc.git_host import GitHubClient
from aidlc.logging import get_logger
from aidlc.openproject import OpenProjectClient
from aidlc.openproject.models import WorkPackage
from aidlc.workflows.task_to_code_local import (
    TaskToCodeLocalResult,
    run_task_to_code_local,
)

log = get_logger(__name__)


@dataclass
class CodeAllLocalResult:
    parent_work_package_id: int
    successes: list[TaskToCodeLocalResult] = field(default_factory=list)
    failures: list[tuple[int, str]] = field(default_factory=list)  # (wp_id, error)


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
    """Run code-gen for every child task of ``parent_work_package_id`` in ID order.

    We fetch children by listing work packages in the project and filtering
    by parent link — ``WorkPackage.parent_id`` is already extracted from
    the HAL payload in the model layer.
    """
    project = project_identifier or op.get_work_package(parent_work_package_id).project_identifier
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

    result = CodeAllLocalResult(parent_work_package_id=parent_work_package_id)
    for child in children:
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
            )
            result.successes.append(r)
            log.info("code_all_local.child_ok", wp=child.id, pr=r.pr_number)
        except Exception as exc:  # one bad task should not kill the batch
            log.error("code_all_local.child_failed", wp=child.id, error=str(exc))
            result.failures.append((child.id, str(exc)[:500]))
    return result
