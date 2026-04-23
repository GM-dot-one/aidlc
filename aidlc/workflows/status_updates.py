"""Stage 4 — Status updates.

Polls each work package that has a linked PR, compares current state to the
last snapshot, and if anything changed (PR merged, PR closed, CI failed)
updates the OpenProject ticket status + leaves a summary comment.

Designed to be called on a cron-like cadence (e.g. every 5 minutes) — safe
to run repeatedly because it reads state from the DB snapshot and no-ops
when nothing has changed.
"""

from __future__ import annotations

from dataclasses import dataclass

from aidlc import db
from aidlc.git_host import GitHubClient
from aidlc.logging import get_logger
from aidlc.openproject import OpenProjectClient

log = get_logger(__name__)

# Status names we'll look up when transitioning. Again, flexible because
# OpenProject admins often rename these.
STATUS_IN_REVIEW = ["In review", "Code review", "In progress"]
STATUS_DONE = ["Closed", "Done", "Resolved", "Merged"]
STATUS_REOPEN = ["In progress", "Rejected"]


@dataclass
class StatusChange:
    work_package_id: int
    pr_number: int
    transition: str  # e.g. "merged", "ci_failed", "closed_unmerged", "no_change"
    new_status: str | None


def _find_first_status(op: OpenProjectClient, names: list[str]) -> tuple[int, str] | None:
    for name in names:
        s = op.find_status_by_name(name)
        if s is not None:
            return s.id, s.name
    return None


def run_status_updates(
    *,
    op: OpenProjectClient,
    gh: GitHubClient,
) -> list[StatusChange]:
    """Walk every tracked work package and react to PR/CI state changes."""
    from sqlmodel import Session, select

    engine = db.get_engine()
    with Session(engine) as session:
        snapshots = list(
            session.exec(select(db.StatusSnapshot).where(db.StatusSnapshot.pr_number.is_not(None)))  # type: ignore[union-attr]
        )

    changes: list[StatusChange] = []
    for snap in snapshots:
        if snap.pr_number is None:
            continue
        pr = gh.get_pull_request(snap.pr_number)
        ci = gh.ci_conclusion(pr.head_sha)

        if pr.state == snap.pr_state and ci == snap.ci_conclusion:
            changes.append(
                StatusChange(
                    work_package_id=snap.work_package_id,
                    pr_number=snap.pr_number,
                    transition="no_change",
                    new_status=None,
                )
            )
            continue

        transition = "other"
        new_status_name: str | None = None

        if pr.merged and snap.pr_state != "closed":
            resolved = _find_first_status(op, STATUS_DONE)
            transition = "merged"
            if resolved is not None:
                status_id, new_status_name = resolved
                wp = op.get_work_package(snap.work_package_id)
                op.update_work_package(wp, status_id=status_id)
            op.add_comment(
                snap.work_package_id,
                f"PR #{pr.number} was merged. Work package moved to "
                f"**{new_status_name or 'Done'}**.",
            )
        elif pr.state == "closed" and not pr.merged:
            resolved = _find_first_status(op, STATUS_REOPEN)
            transition = "closed_unmerged"
            if resolved is not None:
                status_id, new_status_name = resolved
                wp = op.get_work_package(snap.work_package_id)
                op.update_work_package(wp, status_id=status_id)
            op.add_comment(
                snap.work_package_id,
                f"PR #{pr.number} was closed without merging. Flagging for re-triage.",
            )
        elif ci == "failure" and snap.ci_conclusion != "failure":
            transition = "ci_failed"
            op.add_comment(
                snap.work_package_id,
                f"CI failed on PR #{pr.number} (commit `{pr.head_sha[:8]}`). Please investigate.",
            )
        elif ci == "success" and snap.ci_conclusion != "success" and pr.state == "open":
            transition = "ci_passed"
            resolved = _find_first_status(op, STATUS_IN_REVIEW)
            if resolved is not None:
                status_id, new_status_name = resolved
                wp = op.get_work_package(snap.work_package_id)
                op.update_work_package(wp, status_id=status_id)
            op.add_comment(
                snap.work_package_id,
                f"CI passed on PR #{pr.number}. Ready for human review.",
            )

        # Persist new snapshot
        db.upsert_snapshot(
            db.StatusSnapshot(
                work_package_id=snap.work_package_id,
                wp_status=new_status_name or snap.wp_status,
                pr_number=snap.pr_number,
                pr_state="closed" if pr.state == "closed" or pr.merged else "open",
                ci_conclusion=ci,
            )
        )
        db.record_run(
            stage="status_updates",
            work_package_id=snap.work_package_id,
            status="ok",
            pr_url=pr.url,
            notes=transition,
        )
        changes.append(
            StatusChange(
                work_package_id=snap.work_package_id,
                pr_number=snap.pr_number,
                transition=transition,
                new_status=new_status_name,
            )
        )
        log.info(
            "status_updates.change",
            wp=snap.work_package_id,
            pr=snap.pr_number,
            transition=transition,
            new_status=new_status_name,
        )

    return changes
