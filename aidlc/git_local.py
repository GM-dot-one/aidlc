"""Git operations on a local clone of the target repo.

Used by ``task_to_code_local`` to prepare a fresh working directory for a
coding agent, commit the agent's changes, and push the feature branch.

Design notes:

- We authenticate pushes by embedding the PAT in the remote URL
  (``https://x-access-token:{token}@github.com/{owner}/{repo}.git``). This
  keeps token handling local to this module and works with both classic
  and fine-grained tokens. The ``.git/config`` inside the workdir will
  contain the token, so the workdir itself must live under ``.aidlc/``
  which is ``.gitignore``'d at the repo root.
- Subprocess calls use ``check=True`` plus ``capture_output=True`` so that
  failures surface full stderr in the exception, not a cryptic exit code.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from aidlc.logging import get_logger

log = get_logger(__name__)


class GitError(RuntimeError):
    def __init__(self, cmd: list[str], returncode: int, stderr: str) -> None:
        super().__init__(f"git {' '.join(cmd[1:])} exited {returncode}\n{stderr[:1000]}")
        self.cmd = cmd
        self.returncode = returncode
        self.stderr = stderr


def _run(cmd: list[str], *, cwd: Path | None = None) -> str:
    log.debug("git.run", cmd=cmd, cwd=str(cwd) if cwd else None)
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise GitError(cmd, proc.returncode, proc.stderr)
    return proc.stdout


@dataclass
class RepoCheckout:
    """Handle to a prepared local clone ready for a coding agent."""

    path: Path
    branch: str
    base_branch: str
    base_sha: str


def authenticated_url(*, repo: str, token: str) -> str:
    """Build a ``https://x-access-token:{token}@github.com/{repo}.git`` URL."""
    return f"https://x-access-token:{token}@github.com/{repo}.git"


def prepare_branch(
    *,
    workdir_root: Path,
    repo: str,
    token: str,
    base_branch: str,
    branch: str,
    task_id: int,
) -> RepoCheckout:
    """Clone (or refresh) the repo into ``workdir_root/wp-{task_id}`` and cut ``branch``.

    Idempotent: if the workdir exists, we fetch + hard-reset to
    ``origin/{base_branch}`` rather than re-cloning. If ``branch`` already
    exists locally we delete it and recreate — the agent's previous work
    for this WP is assumed to be either pushed or disposable.
    """
    workdir_root.mkdir(parents=True, exist_ok=True)
    path = workdir_root / f"wp-{task_id}"
    url = authenticated_url(repo=repo, token=token)

    if (path / ".git").exists():
        log.info("git.reusing_checkout", path=str(path))
        _run(["git", "remote", "set-url", "origin", url], cwd=path)
        _run(["git", "fetch", "origin", "--prune"], cwd=path)
        _run(["git", "checkout", base_branch], cwd=path)
        _run(["git", "reset", "--hard", f"origin/{base_branch}"], cwd=path)
        # Delete prior feature branch if it exists.
        branches = _run(["git", "branch", "--list", branch], cwd=path).strip()
        if branches:
            _run(["git", "branch", "-D", branch], cwd=path)
    else:
        log.info("git.cloning", repo=repo, into=str(path))
        _run(
            [
                "git",
                "clone",
                "--depth",
                "50",
                "--branch",
                base_branch,
                url,
                str(path),
            ]
        )

    base_sha = _run(["git", "rev-parse", "HEAD"], cwd=path).strip()
    _run(["git", "checkout", "-b", branch], cwd=path)
    return RepoCheckout(path=path, branch=branch, base_branch=base_branch, base_sha=base_sha)


def has_changes(checkout: RepoCheckout) -> bool:
    status = _run(["git", "status", "--porcelain"], cwd=checkout.path).strip()
    return bool(status)


def changed_files(checkout: RepoCheckout) -> list[str]:
    """Paths changed against the base SHA. Includes adds/modifies/deletes.

    Called before commit, so we prefer porcelain with ``--untracked-files=all``
    to enumerate every new file (rather than just the top-level directory).
    If a commit already exists on the branch we also union in ``git diff``
    against the base SHA so rename/edit entries aren't lost.
    """
    diff_out = _run(
        ["git", "diff", "--name-only", checkout.base_sha],
        cwd=checkout.path,
    ).strip()
    status_out = _run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=checkout.path,
    ).strip()
    paths: list[str] = []
    if diff_out:
        paths.extend(ln.strip() for ln in diff_out.splitlines() if ln.strip())
    for line in status_out.splitlines():
        if len(line) < 3:
            continue
        # Porcelain v1 format: XY <path> (optionally -> <renamed>)
        rest = line[3:]
        if " -> " in rest:
            rest = rest.split(" -> ", 1)[1]
        rest = rest.strip().strip('"')
        if rest:
            paths.append(rest)
    # Preserve order, de-dupe.
    seen: set[str] = set()
    unique: list[str] = []
    for p in paths:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return unique


def commit_all(
    *,
    checkout: RepoCheckout,
    message: str,
    author_name: str = "AI-DLC Agent",
    author_email: str = "ai-dlc@localhost",
) -> str:
    """Stage everything and make a single commit. Returns the new SHA."""
    _run(["git", "add", "-A"], cwd=checkout.path)
    _run(
        [
            "git",
            "-c",
            f"user.name={author_name}",
            "-c",
            f"user.email={author_email}",
            "commit",
            "-m",
            message,
        ],
        cwd=checkout.path,
    )
    return _run(["git", "rev-parse", "HEAD"], cwd=checkout.path).strip()


def push_branch(checkout: RepoCheckout) -> None:
    _run(["git", "push", "origin", checkout.branch], cwd=checkout.path)


__all__ = [
    "GitError",
    "RepoCheckout",
    "authenticated_url",
    "changed_files",
    "commit_all",
    "has_changes",
    "prepare_branch",
    "push_branch",
]
