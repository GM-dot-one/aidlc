"""In-memory fakes for LLM / OpenProject / GitHub.

We use fakes (not mocks) so tests read naturally and the fakes double as
executable documentation of the collaborators' contracts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from aidlc.coding_agents import CodingResult
from aidlc.git_host import PullRequest
from aidlc.openproject import Status, Type, WorkPackage

# ---------- LLM ------------------------------------------------------------


@dataclass
class FakeLLM:
    """Returns pre-programmed responses in FIFO order."""

    model: str = "fake-model"
    responses: list[str] = field(default_factory=list)
    calls: list[dict[str, Any]] = field(default_factory=list)

    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> str:
        self.calls.append(
            {
                "system": system,
                "user": user,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
        )
        if not self.responses:
            raise AssertionError("FakeLLM ran out of responses — test mis-configured")
        return self.responses.pop(0)


# ---------- Coding agent ---------------------------------------------------


@dataclass
class FakeCodingAgent:
    """Writes a pre-programmed set of files into the workdir when invoked.

    Mirrors the Claude Code contract: the agent edits files on disk, the
    workflow commits them. Each entry in ``files_to_write`` is a (relative
    path, content) tuple.
    """

    name: str = "fake-agent"
    summary: str = "implemented task"
    files_to_write: list[tuple[str, str]] = field(default_factory=list)
    turns: int | None = 3
    cost_usd: float | None = 0.01
    calls: list[dict[str, Any]] = field(default_factory=list)
    raise_on_invoke: Exception | None = None

    def implement(self, *, prompt: str, workdir: Path) -> CodingResult:
        self.calls.append({"prompt": prompt, "workdir": str(workdir)})
        if self.raise_on_invoke is not None:
            raise self.raise_on_invoke
        for rel, content in self.files_to_write:
            target = workdir / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
        return CodingResult(
            summary=self.summary,
            raw_output="(fake)",
            turns=self.turns,
            cost_usd=self.cost_usd,
        )


# ---------- OpenProject ----------------------------------------------------


@dataclass
class FakeOpenProject:
    """In-memory OpenProject. Only implements methods the agent calls."""

    statuses: list[Status] = field(
        default_factory=lambda: [
            Status(id=1, name="New", isClosed=False),
            Status(id=2, name="In progress", isClosed=False),
            Status(id=3, name="Specified", isClosed=False),
            Status(id=4, name="In review", isClosed=False),
            Status(id=5, name="Closed", isClosed=True),
        ]
    )
    types: list[Type] = field(
        default_factory=lambda: [
            Type(id=1, name="Task"),
            Type(id=2, name="Feature"),
            Type(id=3, name="Bug"),
            Type(id=4, name="Epic"),
        ]
    )
    work_packages: dict[int, WorkPackage] = field(default_factory=dict)
    comments: list[tuple[int, str]] = field(default_factory=list)
    next_id: int = 1000

    # Helper for tests
    def add_wp(
        self,
        *,
        subject: str,
        description: str = "",
        status_name: str = "New",
        type_name: str = "Feature",
        project_identifier: str = "ai-dlc-demo",
    ) -> WorkPackage:
        wp = WorkPackage(
            id=self.next_id,
            subject=subject,
            description_text=description,
            status_id=next(s.id for s in self.statuses if s.name == status_name),
            status_name=status_name,
            type_id=next(t.id for t in self.types if t.name == type_name),
            type_name=type_name,
            project_identifier=project_identifier,
            lock_version=1,
        )
        self.work_packages[wp.id] = wp
        self.next_id += 1
        return wp

    # --- client surface ---

    def get_work_package(self, wp_id: int) -> WorkPackage:
        return self.work_packages[wp_id]

    def create_work_package(
        self,
        *,
        project_identifier: str,
        subject: str,
        description: str,
        type_id: int,
        parent_id: int | None = None,
    ) -> WorkPackage:
        type_name = next((t.name for t in self.types if t.id == type_id), "Task")
        wp = WorkPackage(
            id=self.next_id,
            subject=subject,
            description_text=description,
            status_id=1,
            status_name="New",
            type_id=type_id,
            type_name=type_name,
            project_identifier=project_identifier,
            parent_id=parent_id,
            lock_version=1,
        )
        self.work_packages[wp.id] = wp
        self.next_id += 1
        return wp

    def update_work_package(
        self,
        wp: WorkPackage,
        *,
        description: str | None = None,
        status_id: int | None = None,
        subject: str | None = None,
    ) -> WorkPackage:
        stored = self.work_packages[wp.id]
        if description is not None:
            stored.description_text = description
        if subject is not None:
            stored.subject = subject
        if status_id is not None:
            stored.status_id = status_id
            stored.status_name = next(
                (s.name for s in self.statuses if s.id == status_id), stored.status_name
            )
        stored.lock_version += 1
        return stored

    def add_comment(self, wp_id: int, markdown: str) -> None:
        self.comments.append((wp_id, markdown))

    def list_types(self) -> list[Type]:
        return list(self.types)

    def list_statuses(self) -> list[Status]:
        return list(self.statuses)

    def find_type_by_name(self, name: str) -> Type | None:
        return next((t for t in self.types if t.name.lower() == name.lower()), None)

    def find_status_by_name(self, name: str) -> Status | None:
        return next((s for s in self.statuses if s.name.lower() == name.lower()), None)

    def close(self) -> None:  # parity with real client
        pass


# ---------- GitHub ---------------------------------------------------------


@dataclass
class FakeGitHub:
    base_sha: str = "a" * 40
    next_pr: int = 100
    prs: dict[int, PullRequest] = field(default_factory=dict)
    branches: dict[str, str] = field(default_factory=dict)
    files: dict[tuple[str, str], str] = field(default_factory=dict)  # (branch, path) -> content
    ci_by_sha: dict[str, str | None] = field(default_factory=dict)

    def get_branch_sha(self, branch: str) -> str:
        return self.branches.get(branch, self.base_sha)

    def create_branch(self, *, new_branch: str, from_sha: str) -> None:
        if new_branch in self.branches:
            raise RuntimeError(f"branch {new_branch} already exists")
        self.branches[new_branch] = from_sha

    def commit_file(self, *, branch: str, path: str, content: str, message: str) -> str:
        self.files[(branch, path)] = content
        new_sha = f"commit-{len(self.files):040d}"
        self.branches[branch] = new_sha
        return new_sha

    def open_pull_request(
        self, *, title: str, body: str, head: str, base: str, draft: bool = False
    ) -> PullRequest:
        number = self.next_pr
        self.next_pr += 1
        # Tolerate branches created out-of-band (e.g. pushed via real git in
        # task_to_code_local tests) — we don't know the SHA so we fabricate one.
        head_sha = self.branches.get(head) or f"remote-{head}"[:40].ljust(40, "0")
        pr = PullRequest(
            number=number,
            url=f"https://github.com/acme/repo/pull/{number}",
            head_sha=head_sha,
            state="open",
            merged=False,
        )
        self.prs[number] = pr
        return pr

    def get_pull_request(self, number: int) -> PullRequest:
        return self.prs[number]

    def ci_conclusion(self, sha: str) -> str | None:
        return self.ci_by_sha.get(sha)

    def close(self) -> None:
        pass
