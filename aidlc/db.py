"""Lightweight persistence layer for agent run state.

We keep a local SQLite DB so re-runs are idempotent — the agent remembers
which work packages it has already spec'd, decomposed, or coded, and which
PRs it has opened. This matters for the ``status_updates`` loop, which needs
to detect transitions without re-processing every ticket on every tick.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import event
from sqlmodel import Field, Session, SQLModel, create_engine, select

from aidlc.config import get_settings

if sys.version_info >= (3, 11):  # noqa: UP036 — intentional runtime fallback for 3.10
    from datetime import UTC
else:  # pragma: no cover - 3.10 fallback
    from datetime import timezone

    UTC = timezone.utc  # type: ignore[misc, assignment]  # noqa: UP017


def _utc_now() -> datetime:
    return datetime.now(UTC)


class WorkflowRun(SQLModel, table=True):
    """One execution of a workflow stage against a given work package."""

    __tablename__ = "workflow_runs"

    id: int | None = Field(default=None, primary_key=True)
    stage: str = Field(index=True)  # idea_to_spec, spec_to_tasks, task_to_code, status_updates
    work_package_id: int = Field(index=True)
    status: str = Field(default="ok")  # ok, error
    pr_url: str | None = Field(default=None)
    branch_name: str | None = Field(default=None)
    notes: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=_utc_now)


class StatusSnapshot(SQLModel, table=True):
    """Last-seen remote state for a work package + linked PR.

    Used by the status_updates workflow to detect transitions cheaply.
    """

    __tablename__ = "status_snapshots"

    work_package_id: int = Field(primary_key=True)
    wp_status: str | None = Field(default=None)
    pr_number: int | None = Field(default=None)
    pr_state: str | None = Field(default=None)  # open, closed, merged
    ci_conclusion: str | None = Field(default=None)  # success, failure, pending
    updated_at: datetime = Field(default_factory=_utc_now)


_engine: Any = None


def _set_wal_mode(dbapi_conn: Any, _connection_record: Any) -> None:
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


def get_engine() -> Any:
    """Lazily create the SQLite engine and ensure parent dirs exist."""
    global _engine
    if _engine is None:
        db_path = get_settings().aidlc_db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(f"sqlite:///{db_path}", echo=False)
        event.listen(_engine, "connect", _set_wal_mode)
        SQLModel.metadata.create_all(_engine)
    return _engine


def reset_engine() -> None:
    """Used by tests to force a fresh engine after changing settings."""
    global _engine
    _engine = None


def record_run(
    *,
    stage: str,
    work_package_id: int,
    status: str = "ok",
    pr_url: str | None = None,
    branch_name: str | None = None,
    notes: str | None = None,
) -> WorkflowRun:
    run = WorkflowRun(
        stage=stage,
        work_package_id=work_package_id,
        status=status,
        pr_url=pr_url,
        branch_name=branch_name,
        notes=notes,
    )
    with Session(get_engine()) as session:
        session.add(run)
        session.commit()
        session.refresh(run)
    return run


def has_run(stage: str, work_package_id: int) -> bool:
    """Check whether we've already executed a stage on this work package."""
    with Session(get_engine()) as session:
        result = session.exec(
            select(WorkflowRun)
            .where(WorkflowRun.stage == stage)
            .where(WorkflowRun.work_package_id == work_package_id)
            .where(WorkflowRun.status == "ok")
        ).first()
    return result is not None


def upsert_snapshot(snapshot: StatusSnapshot) -> StatusSnapshot:
    snapshot.updated_at = _utc_now()
    with Session(get_engine()) as session:
        existing = session.get(StatusSnapshot, snapshot.work_package_id)
        if existing is None:
            session.add(snapshot)
        else:
            existing.wp_status = snapshot.wp_status
            existing.pr_number = snapshot.pr_number
            existing.pr_state = snapshot.pr_state
            existing.ci_conclusion = snapshot.ci_conclusion
            existing.updated_at = snapshot.updated_at
        session.commit()
    return snapshot


def get_snapshot(work_package_id: int) -> StatusSnapshot | None:
    with Session(get_engine()) as session:
        return session.get(StatusSnapshot, work_package_id)


def get_run_notes(stage: str, work_package_id: int) -> str | None:
    """Retrieve the notes from the last successful run of a given stage."""
    with Session(get_engine()) as session:
        run = session.exec(
            select(WorkflowRun)
            .where(WorkflowRun.stage == stage)
            .where(WorkflowRun.work_package_id == work_package_id)
            .where(WorkflowRun.status == "ok")
            .order_by(WorkflowRun.created_at.desc())  # type: ignore[attr-defined]
        ).first()
    return run.notes if run else None


def set_db_path_for_tests(path: Path) -> None:
    """Helper so pytest can point the engine at a temp DB."""
    from aidlc.config import get_settings as _gs

    _gs.cache_clear()
    _gs().aidlc_db_path = path
    reset_engine()
