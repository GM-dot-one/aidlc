"""Typer-based CLI — the operator interface for the AI-DLC agent.

Commands roughly mirror the workflow stages:
    aidlc spec <wp-id>
    aidlc decompose <wp-id>
    aidlc code <wp-id>             # one-shot LLM scaffold (cheap)
    aidlc code-local <wp-id>       # run Claude Code locally, push, open PR
    aidlc code-all-local <parent-wp-id>  # batch Claude Code across children
    aidlc watch
    aidlc review <wp-id>           # AI-review a single PR, auto-merge if clean
    aidlc review-all <parent-wp-id>  # review & merge all children with open PRs
    aidlc run-all <wp-id>          # chain the three authoring stages
    aidlc doctor                   # sanity-check configuration
"""

from __future__ import annotations

import json
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from aidlc.coding_agents import ClaudeCodeAgent
from aidlc.config import get_settings
from aidlc.git_host import GitHubClient
from aidlc.llm import get_llm
from aidlc.logging import get_logger
from aidlc.openproject import OpenProjectClient
from aidlc.workflows import (
    run_code_all_local,
    run_idea_to_spec,
    run_review_all,
    run_review_and_merge,
    run_spec_to_tasks,
    run_status_updates,
    run_task_to_code,
    run_task_to_code_local,
)

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="AI-DLC agent — drives a feature through spec, decomposition, code, and status updates.",
)
log = get_logger(__name__)
console = Console()


def _op_client() -> OpenProjectClient:
    s = get_settings()
    return OpenProjectClient(
        base_url=s.openproject_url,
        api_key=s.openproject_api_key.get_secret_value(),
    )


def _gh_client() -> GitHubClient:
    s = get_settings()
    token, repo = s.require_github()
    return GitHubClient(token=token.get_secret_value(), repo=repo)


def _claude_agent() -> ClaudeCodeAgent:
    s = get_settings()
    return ClaudeCodeAgent(
        bin_path=s.claude_code_bin,
        permission_mode=s.claude_code_permission_mode,
        max_turns=s.claude_code_max_turns,
        timeout_s=s.claude_code_timeout_s,
    )


@app.command()
def spec(
    wp_id: Annotated[int, typer.Argument(help="Work package ID to spec")],
    force: Annotated[bool, typer.Option("--force", help="Re-run even if already done")] = False,
) -> None:
    """Stage 1 — draft a spec from a raw idea work package."""
    llm = get_llm()
    with _op_client() as op:
        result = run_idea_to_spec(llm=llm, op=op, work_package_id=wp_id, force=force)
    console.print(
        f"[green]✓ Spec written to WP #{result.work_package_id}[/] "
        f"(status → {result.transitioned_to or '—'})"
    )


@app.command()
def decompose(
    wp_id: Annotated[int, typer.Argument(help="Parent (spec'd) work package to decompose")],
    force: Annotated[bool, typer.Option("--force")] = False,
) -> None:
    """Stage 2 — decompose a spec into child tasks."""
    s = get_settings()
    llm = get_llm()
    with _op_client() as op:
        result = run_spec_to_tasks(
            llm=llm,
            op=op,
            parent_work_package_id=wp_id,
            project_identifier=s.openproject_project,
            force=force,
        )
    console.print(
        f"[green]✓ Created {len(result.created_task_ids)} child tasks[/] "
        f"under WP #{result.parent_work_package_id}: {result.created_task_ids}"
    )


@app.command()
def code(
    wp_id: Annotated[int, typer.Argument(help="Task work package to implement")],
    hints: Annotated[
        str,
        typer.Option(help="Stack hints for the LLM, e.g. 'Ruby on Rails + RSpec'"),
    ] = "Python / FastAPI / pytest (adjust if your repo differs)",
    force: Annotated[bool, typer.Option("--force")] = False,
) -> None:
    """Stage 3 — generate a scaffold PR for a task."""
    s = get_settings()
    llm = get_llm()
    with _op_client() as op, _gh_client() as gh:
        result = run_task_to_code(
            llm=llm,
            op=op,
            gh=gh,
            work_package_id=wp_id,
            repo=s.github_repo or "",
            base_branch=s.github_base_branch,
            stack_hints=hints,
            force=force,
        )
    console.print(
        f"[green]✓ Opened PR #{result.pr_number}[/] on branch "
        f"[cyan]{result.branch}[/]: {result.pr_url}"
    )


@app.command("code-local")
def code_local(
    wp_id: Annotated[int, typer.Argument(help="Task work package to implement")],
    hints: Annotated[
        str,
        typer.Option(help="Stack hints Claude will verify by reading the repo"),
    ] = "(inspect the repo to determine the stack)",
    force: Annotated[bool, typer.Option("--force")] = False,
) -> None:
    """Stage 3b — run Claude Code on a local clone and open a draft PR."""
    s = get_settings()
    token, repo = s.require_github()
    agent = _claude_agent()
    with _op_client() as op, _gh_client() as gh:
        result = run_task_to_code_local(
            agent=agent,
            op=op,
            gh=gh,
            work_package_id=wp_id,
            repo=repo,
            github_token=token.get_secret_value(),
            base_branch=s.github_base_branch,
            workdir_root=s.aidlc_workdir,
            stack_hints=hints,
            force=force,
        )
    console.print(
        f"[green]✓ Opened PR #{result.pr_number}[/] on [cyan]{result.branch}[/]: "
        f"{result.pr_url}\n  ({len(result.changed_files)} files changed by {agent.name})"
    )


@app.command("code-all-local")
def code_all_local(
    parent_wp_id: Annotated[int, typer.Argument(help="Parent (decomposed) WP id")],
    hints: Annotated[
        str,
        typer.Option(help="Stack hints Claude will verify by reading the repo"),
    ] = "(inspect the repo to determine the stack)",
    force: Annotated[bool, typer.Option("--force")] = False,
) -> None:
    """Run Claude Code on every child task of a decomposed parent, sequentially."""
    s = get_settings()
    token, repo = s.require_github()
    agent = _claude_agent()
    with _op_client() as op, _gh_client() as gh:
        result = run_code_all_local(
            agent=agent,
            op=op,
            gh=gh,
            parent_work_package_id=parent_wp_id,
            repo=repo,
            github_token=token.get_secret_value(),
            base_branch=s.github_base_branch,
            workdir_root=s.aidlc_workdir,
            stack_hints=hints,
            force=force,
            project_identifier=s.openproject_project,
        )

    table = Table(title=f"code-all-local — parent WP #{parent_wp_id}")
    table.add_column("WP")
    table.add_column("Outcome")
    table.add_column("Detail")
    for ok in result.successes:
        table.add_row(str(ok.work_package_id), "[green]✓ PR[/]", f"#{ok.pr_number} {ok.pr_url}")
    for wp_id, err in result.failures:
        table.add_row(str(wp_id), "[red]✗ failed[/]", err[:120])
    console.print(table)
    console.print(f"[bold]Done:[/] {len(result.successes)} ok, {len(result.failures)} failed")


@app.command()
def watch() -> None:
    """Stage 4 — one tick of status updates across tracked PRs."""
    with _op_client() as op, _gh_client() as gh:
        changes = run_status_updates(op=op, gh=gh)

    table = Table(title=f"Status tick — {len(changes)} tracked work packages")
    table.add_column("WP")
    table.add_column("PR")
    table.add_column("Transition", style="cyan")
    table.add_column("New status")
    for c in changes:
        table.add_row(
            str(c.work_package_id),
            f"#{c.pr_number}",
            c.transition,
            c.new_status or "—",
        )
    console.print(table)


@app.command()
def review(
    wp_id: Annotated[int, typer.Argument(help="Work package ID with a linked PR to review")],
    force: Annotated[bool, typer.Option("--force", help="Re-review even if already done")] = False,
) -> None:
    """Stage 5 — AI-review a PR linked to a work package and auto-merge if approved + CI green."""
    s = get_settings()
    llm = get_llm()
    with _op_client() as op, _gh_client() as gh:
        result = run_review_and_merge(
            llm=llm,
            op=op,
            gh=gh,
            work_package_id=wp_id,
            repo=s.github_repo or "",
            force=force,
        )
    merged_tag = " and [green]merged[/]" if result.merged else ""
    console.print(
        f"[green]✓ Reviewed PR #{result.pr_number}[/] — verdict: "
        f"[cyan]{result.verdict}[/]{merged_tag}\n  {result.summary[:200]}"
    )


@app.command("review-all")
def review_all(
    parent_wp_id: Annotated[int, typer.Argument(help="Parent WP whose children to review")],
    force: Annotated[bool, typer.Option("--force", help="Re-review even if already done")] = False,
) -> None:
    """Review and merge all children of a parent WP that have open PRs."""
    s = get_settings()
    llm = get_llm()
    with _op_client() as op, _gh_client() as gh:
        result = run_review_all(
            llm=llm,
            op=op,
            gh=gh,
            parent_work_package_id=parent_wp_id,
            repo=s.github_repo or "",
            project_identifier=s.openproject_project,
            force=force,
        )

    table = Table(title=f"review-all — parent WP #{parent_wp_id}")
    table.add_column("WP")
    table.add_column("PR")
    table.add_column("Verdict", style="cyan")
    table.add_column("Merged")
    table.add_column("Detail")
    for ok in result.successes:
        table.add_row(
            str(ok.work_package_id),
            f"#{ok.pr_number}",
            ok.verdict,
            "[green]yes[/]" if ok.merged else "no",
            ok.summary[:120],
        )
    for wp_id, err in result.failures:
        table.add_row(str(wp_id), "—", "[red]error[/]", "—", err[:120])
    console.print(table)
    merged_count = sum(1 for r in result.successes if r.merged)
    console.print(
        f"[bold]Done:[/] {len(result.successes)} reviewed, "
        f"{merged_count} merged, {len(result.failures)} failed"
    )


@app.command("run-all")
def run_all(
    wp_id: Annotated[int, typer.Argument(help="Idea work package ID to drive end-to-end")],
    hints: Annotated[str, typer.Option(help="Stack hints for code stage")] = (
        "Python / FastAPI / pytest (adjust if your repo differs)"
    ),
    skip_code: Annotated[bool, typer.Option("--skip-code", help="Stop after decompose")] = False,
) -> None:
    """Chain stages 1 → 2 → 3 on a single idea. Code stage targets the first child task."""
    s = get_settings()
    llm = get_llm()
    with _op_client() as op:
        spec_result = run_idea_to_spec(llm=llm, op=op, work_package_id=wp_id)
        console.print(f"[green]✓ spec[/] for WP #{spec_result.work_package_id}")

        decomp = run_spec_to_tasks(
            llm=llm,
            op=op,
            parent_work_package_id=wp_id,
            project_identifier=s.openproject_project,
        )
        console.print(
            f"[green]✓ decompose[/] → {len(decomp.created_task_ids)} children: "
            f"{decomp.created_task_ids}"
        )

        if skip_code or not decomp.created_task_ids:
            return

        first = decomp.created_task_ids[0]
        with _gh_client() as gh:
            code_result = run_task_to_code(
                llm=llm,
                op=op,
                gh=gh,
                work_package_id=first,
                repo=s.github_repo or "",
                base_branch=s.github_base_branch,
                stack_hints=hints,
            )
        console.print(f"[green]✓ code[/] PR #{code_result.pr_number} → {code_result.pr_url}")


@app.command()
def doctor() -> None:
    """Validate configuration + connectivity without mutating anything."""
    s = get_settings()
    report: dict[str, str] = {}
    report["openproject_url"] = s.openproject_url
    report["project"] = s.openproject_project
    report["llm_provider"] = s.aidlc_llm_provider.value
    report["llm_model"] = (
        s.groq_model if s.aidlc_llm_provider.value == "groq" else s.anthropic_model
    )
    report["github_repo"] = s.github_repo or "(not configured)"
    report["db_path"] = str(s.aidlc_db_path)

    try:
        with _op_client() as op:
            statuses = op.list_statuses()
            types = op.list_types()
        report["openproject_statuses"] = ", ".join(st.name for st in statuses[:8]) + (
            "…" if len(statuses) > 8 else ""
        )
        report["openproject_types"] = ", ".join(t.name for t in types[:8])
    except Exception as exc:  # doctor output is for humans
        report["openproject_error"] = str(exc)

    if s.github_token is not None and s.github_repo is not None:
        try:
            with _gh_client() as gh:
                sha = gh.get_branch_sha(s.github_base_branch)
            report["github_base_sha"] = sha[:12]
        except Exception as exc:
            report["github_error"] = str(exc)

    console.print_json(json.dumps(report))


if __name__ == "__main__":
    app()
