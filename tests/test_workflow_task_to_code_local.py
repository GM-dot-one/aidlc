"""Integration test for the Claude-Code-powered task_to_code workflow.

Uses a real local bare git repo as "origin" (no network required) plus the
FakeCodingAgent and in-memory FakeOpenProject/FakeGitHub.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from aidlc import git_local
from aidlc.workflows import run_code_all_local, run_task_to_code_local
from tests.fakes import FakeCodingAgent, FakeGitHub, FakeOpenProject


def _init_bare_origin(root: Path) -> Path:
    origin = root / "origin.git"
    subprocess.run(["git", "init", "--bare", "-b", "main", str(origin)], check=True)

    seed = root / "seed"
    subprocess.run(["git", "clone", str(origin), str(seed)], check=True)
    (seed / "README.md").write_text("# demo\n")
    subprocess.run(
        ["git", "-C", str(seed), "-c", "user.name=x", "-c", "user.email=x@x", "add", "."],
        check=True,
    )
    subprocess.run(
        [
            "git",
            "-C",
            str(seed),
            "-c",
            "user.name=x",
            "-c",
            "user.email=x@x",
            "commit",
            "-m",
            "init",
        ],
        check=True,
    )
    subprocess.run(["git", "-C", str(seed), "branch", "-M", "main"], check=True)
    subprocess.run(["git", "-C", str(seed), "push", "origin", "main"], check=True)
    return origin


@pytest.fixture
def origin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    origin_path = _init_bare_origin(tmp_path)

    # Route all authenticated push URLs to the local bare repo.
    def _local_url(*, repo: str, token: str) -> str:
        _ = repo, token
        return f"file://{origin_path}"

    monkeypatch.setattr(git_local, "authenticated_url", _local_url)
    return origin_path


def test_run_task_to_code_local_happy_path(origin: Path, tmp_path: Path) -> None:
    _ = origin
    op = FakeOpenProject()
    wp = op.add_wp(subject="Add CSV export", description="Add a CSV export endpoint.")
    gh = FakeGitHub(base_sha="whatever")
    agent = FakeCodingAgent(
        files_to_write=[
            ("src/export.py", "def export_csv():\n    pass\n"),
            ("tests/test_export.py", "def test_export():\n    assert True\n"),
        ],
        summary="Added CSV export stub + test",
    )

    result = run_task_to_code_local(
        agent=agent,
        op=op,  # type: ignore[arg-type]
        gh=gh,  # type: ignore[arg-type]
        work_package_id=wp.id,
        repo="acme/erp",
        github_token="ghp_fake",
        base_branch="main",
        workdir_root=tmp_path / "workdir",
    )

    assert result.pr_number >= 100
    assert len(result.changed_files) == 2
    assert "src/export.py" in result.changed_files
    assert len(gh.prs) == 1
    pr = next(iter(gh.prs.values()))
    assert pr.number == result.pr_number
    assert any(wp.id == wp_id for wp_id, _ in op.comments)


def test_skips_when_already_run_without_force(origin: Path, tmp_path: Path) -> None:
    _ = origin
    op = FakeOpenProject()
    wp = op.add_wp(subject="Task A")
    gh = FakeGitHub()
    agent = FakeCodingAgent(files_to_write=[("a.py", "x=1\n")])

    first = run_task_to_code_local(
        agent=agent,
        op=op,  # type: ignore[arg-type]
        gh=gh,  # type: ignore[arg-type]
        work_package_id=wp.id,
        repo="acme/erp",
        github_token="ghp_fake",
        base_branch="main",
        workdir_root=tmp_path / "workdir",
    )

    agent.calls.clear()
    second = run_task_to_code_local(
        agent=agent,
        op=op,  # type: ignore[arg-type]
        gh=gh,  # type: ignore[arg-type]
        work_package_id=wp.id,
        repo="acme/erp",
        github_token="ghp_fake",
        base_branch="main",
        workdir_root=tmp_path / "workdir",
    )

    assert agent.calls == []
    assert second.pr_number == first.pr_number


def test_raises_if_agent_makes_no_changes(origin: Path, tmp_path: Path) -> None:
    _ = origin
    op = FakeOpenProject()
    wp = op.add_wp(subject="Do nothing")
    gh = FakeGitHub()
    agent = FakeCodingAgent(files_to_write=[])

    with pytest.raises(RuntimeError, match="no file changes"):
        run_task_to_code_local(
            agent=agent,
            op=op,  # type: ignore[arg-type]
            gh=gh,  # type: ignore[arg-type]
            work_package_id=wp.id,
            repo="acme/erp",
            github_token="ghp_fake",
            base_branch="main",
            workdir_root=tmp_path / "workdir",
        )


def test_run_code_all_local_iterates_children(origin: Path, tmp_path: Path) -> None:
    _ = origin
    op = FakeOpenProject()
    parent = op.add_wp(subject="Parent spec")
    c1 = op.add_wp(subject="Child A")
    c1.parent_id = parent.id
    c2 = op.add_wp(subject="Child B")
    c2.parent_id = parent.id
    op.add_wp(subject="Unrelated")  # sibling with no parent — must be skipped

    from aidlc.openproject.models import WorkPackage

    def _list(*, project_identifier: str, page_size: int = 50) -> list[WorkPackage]:
        _ = project_identifier, page_size
        return list(op.work_packages.values())

    op.list_work_packages = _list  # type: ignore[attr-defined]

    gh = FakeGitHub()
    agent = FakeCodingAgent(
        files_per_call=[
            [("a.py", "x=1\n")],
            [("b.py", "y=2\n")],
        ],
    )

    result = run_code_all_local(
        agent=agent,
        op=op,  # type: ignore[arg-type]
        gh=gh,  # type: ignore[arg-type]
        parent_work_package_id=parent.id,
        repo="acme/erp",
        github_token="ghp_fake",
        base_branch="main",
        workdir_root=tmp_path / "workdir",
        project_identifier="ai-dlc-demo",
    )

    assert len(result.successes) == 2
    assert len(result.failures) == 0
    assert {r.work_package_id for r in result.successes} == {c1.id, c2.id}
    assert result.pr_number >= 100
    assert len(gh.prs) == 1
