"""Batch driver — run ``review_and_merge`` across all children of a parent WP.

Sequential, not parallel: we merge one PR at a time and try to update the
next PR's branch after each merge so it stays current with the base branch.
A failed review is logged but does not abort the batch — the operator can
re-run just the failures with ``--force``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from aidlc import db
from aidlc.git_host import GitHubClient, GitHubError
from aidlc.llm.base import LLMProvider
from aidlc.logging import get_logger
from aidlc.openproject import OpenProjectClient
from aidlc.openproject.models import WorkPackage
from aidlc.workflows.review_and_merge import (
    ReviewAndMergeResult,
    run_review_and_merge,
)

log = get_logger(__name__)


@dataclass
class ReviewAllResult:
    parent_work_package_id: int
    successes: list[ReviewAndMergeResult] = field(default_factory=list)
    failures: list[tuple[int, str]] = field(default_factory=list)  # (wp_id, error)


def _children_with_open_prs(
    op: OpenProjectClient,
    parent_work_package_id: int,
    project_identifier: str,
) -> list[tuple[WorkPackage, int]]:
    """Return (WorkPackage, pr_number) pairs for children that have open PRs."""
    all_wps = op.list_work_packages(project_identifier=project_identifier, page_size=200)
    children: list[WorkPackage] = sorted(
        (wp for wp in all_wps if wp.parent_id == parent_work_package_id),
        key=lambda w: w.id,
    )

    result: list[tuple[WorkPackage, int]] = []
    for child in children:
        snapshot = db.get_snapshot(child.id)
        if snapshot is None or snapshot.pr_number is None:
            continue
        if snapshot.pr_state == "closed":
            continue
        result.append((child, snapshot.pr_number))
    return result


def _try_update_branch(gh: GitHubClient, pr_number: int) -> None:
    """Best-effort attempt to update a PR branch after an earlier merge."""
    try:
        gh.update_pull_request_branch(pr_number)
        log.info("review_all.branch_updated", pr=pr_number)
    except GitHubError as exc:
        # 422 = branch already up to date or cannot be updated — not fatal
        log.warning(
            "review_all.branch_update_failed",
            pr=pr_number,
            status=exc.status_code,
            body=exc.body[:200],
        )
    except Exception as exc:
        log.warning("review_all.branch_update_error", pr=pr_number, error=str(exc))


def run_review_all(
    *,
    llm: LLMProvider,
    op: OpenProjectClient,
    gh: GitHubClient,
    parent_work_package_id: int,
    repo: str,
    project_identifier: str | None = None,
    force: bool = False,
) -> ReviewAllResult:
    """Review and merge every child of ``parent_work_package_id`` that has an open PR."""

    project = project_identifier or op.get_work_package(parent_work_package_id).project_identifier
    if project is None:
        raise RuntimeError(
            f"cannot determine project for parent WP {parent_work_package_id}; "
            "pass project_identifier explicitly"
        )

    children_with_prs = _children_with_open_prs(op, parent_work_package_id, project)
    if not children_with_prs:
        raise RuntimeError(
            f"WP #{parent_work_package_id} has no children with open PRs — "
            "run `aidlc code-all-local` first"
        )
    log.info(
        "review_all.start",
        parent=parent_work_package_id,
        reviewable=len(children_with_prs),
    )

    result = ReviewAllResult(parent_work_package_id=parent_work_package_id)
    remaining_prs = [pr_num for _, pr_num in children_with_prs]

    for idx, (child, pr_number) in enumerate(children_with_prs):
        try:
            r = run_review_and_merge(
                llm=llm,
                op=op,
                gh=gh,
                work_package_id=child.id,
                repo=repo,
                force=force,
            )
            result.successes.append(r)
            log.info(
                "review_all.child_ok",
                wp=child.id,
                pr=pr_number,
                verdict=r.verdict,
                merged=r.merged,
            )

            # After a successful merge, try to update the next PR's branch
            if r.merged and idx + 1 < len(children_with_prs):
                next_pr = remaining_prs[idx + 1]
                _try_update_branch(gh, next_pr)

        except Exception as exc:  # one bad review should not kill the batch
            log.error("review_all.child_failed", wp=child.id, error=str(exc))
            result.failures.append((child.id, str(exc)[:500]))

    return result
