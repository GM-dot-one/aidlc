"""Stage 5 — AI code review and auto-merge.

Fetches the PR diff from GitHub, asks the LLM to review it, posts the review
on GitHub.  If CI passes and the review approves, squash-merges the PR and
updates the OpenProject work package status to Done/Closed.

This is the "Level 3" fully autonomous review path — no human in the loop.
Use ``--force`` to re-review a PR that has already been reviewed.
"""

from __future__ import annotations

from dataclasses import dataclass

from aidlc import db
from aidlc.git_host import GitHubClient
from aidlc.llm.base import LLMProvider, extract_json
from aidlc.logging import get_logger
from aidlc.openproject import OpenProjectClient
from aidlc.prompts import render

log = get_logger(__name__)

STATUS_DONE = ["Closed", "Done", "Resolved", "Merged"]


@dataclass
class ReviewAndMergeResult:
    work_package_id: int
    pr_number: int
    verdict: str  # approve | request_changes
    summary: str
    merged: bool


def _find_first_status(op: OpenProjectClient, names: list[str]) -> tuple[int, str] | None:
    for name in names:
        s = op.find_status_by_name(name)
        if s is not None:
            return s.id, s.name
    return None


def run_review_and_merge(
    *,
    llm: LLMProvider,
    op: OpenProjectClient,
    gh: GitHubClient,
    work_package_id: int,
    repo: str,
    force: bool = False,
) -> ReviewAndMergeResult:
    """Review a single PR linked to ``work_package_id`` and merge if appropriate."""

    # ---- guard: already reviewed? ------------------------------------------
    if not force and db.has_run("review", work_package_id):
        log.info("review.skip_already_run", wp=work_package_id)
        snapshot = db.get_snapshot(work_package_id)
        if snapshot is None or snapshot.pr_number is None:
            raise RuntimeError(
                f"work package {work_package_id} marked reviewed but no PR recorded — use --force"
            )
        return ReviewAndMergeResult(
            work_package_id=work_package_id,
            pr_number=snapshot.pr_number,
            verdict="approve",
            summary="(skipped — already reviewed)",
            merged=False,
        )

    # ---- load snapshot & PR ------------------------------------------------
    snapshot = db.get_snapshot(work_package_id)
    if snapshot is None or snapshot.pr_number is None:
        raise RuntimeError(
            f"no PR recorded for work package {work_package_id} — run code-local first"
        )

    pr_number = snapshot.pr_number
    pr = gh.get_pull_request(pr_number)
    if pr.state != "open":
        raise RuntimeError(
            f"PR #{pr_number} is {pr.state}, not open — nothing to review"
        )

    wp = op.get_work_package(work_package_id)
    log.info("review.start", wp=wp.id, subject=wp.subject, pr=pr_number)

    # ---- fetch diff --------------------------------------------------------
    diff = gh.get_pull_request_diff(pr_number)
    if not diff.strip():
        raise RuntimeError(f"PR #{pr_number} has an empty diff — nothing to review")

    # ---- ask LLM to review -------------------------------------------------
    prompt = render(
        "review_pr",
        pr_title=f"[WP-{wp.id}] {wp.subject}",
        pr_diff=diff[:120_000],  # cap so we don't blow context windows
        subject=wp.subject,
        description=(wp.description_text or "").strip() or "(no description provided)",
        wp_id=str(wp.id),
    )
    raw = llm.complete(
        system="You are a meticulous code reviewer. Return only valid JSON.",
        user=prompt,
        max_tokens=4096,
        temperature=0.2,
    )

    try:
        review = extract_json(raw)
    except ValueError as exc:
        db.record_run(
            stage="review",
            work_package_id=wp.id,
            status="error",
            pr_url=pr.url,
            notes=f"LLM returned unparseable response: {exc}"[:500],
        )
        raise RuntimeError(f"LLM review response was not valid JSON: {exc}") from exc

    verdict: str = review.get("verdict", "request_changes")
    summary: str = review.get("summary", "")
    comments: list[dict] = review.get("comments", [])

    log.info("review.llm_verdict", wp=wp.id, verdict=verdict, comments=len(comments))

    # ---- post review on GitHub ---------------------------------------------
    # GitHub forbids REQUEST_CHANGES on your own PR (the token owner opened it).
    # Fall back to COMMENT so the feedback is still posted.
    event = "APPROVE" if verdict == "approve" else "COMMENT"
    review_body = f"**AI-DLC automated review** — verdict: **{verdict}**\n\n{summary}"

    inline_comments = [
        {"path": c["path"], "line": c["line"], "body": c["body"]}
        for c in comments
        if all(k in c for k in ("path", "line", "body"))
    ]

    try:
        gh.create_review(
            number=pr_number,
            body=review_body,
            event=event,
            comments=inline_comments,
        )
    except Exception as review_err:
        # Inline comments with bad line numbers cause "Line could not be resolved".
        # Retry with comments folded into the review body instead.
        log.warning("review.inline_comments_failed", error=str(review_err)[:200])
        if inline_comments:
            folded = "\n\n---\n\n**Inline comments (could not attach to diff):**\n\n"
            for c in inline_comments:
                folded += f"- `{c['path']}` L{c['line']}: {c['body']}\n"
            gh.create_review(
                number=pr_number,
                body=review_body + folded,
                event=event,
                comments=[],
            )
        else:
            raise
    log.info("review.posted", pr=pr_number, review_event=event)

    # ---- merge if CI passes and verdict is approve -------------------------
    merged = False
    if verdict == "approve":
        ci = gh.ci_conclusion(pr.head_sha)
        if ci == "success":
            gh.merge_pull_request(pr_number, merge_method="squash")
            merged = True
            log.info("review.merged", pr=pr_number)

            # Update OpenProject WP status to Done/Closed
            resolved = _find_first_status(op, STATUS_DONE)
            new_status_name: str | None = None
            if resolved is not None:
                status_id, new_status_name = resolved
                op.update_work_package(wp, status_id=status_id)
            op.add_comment(
                wp.id,
                f"AI-DLC review **approved** PR #{pr_number} and squash-merged it. "
                f"Work package moved to **{new_status_name or 'Done'}**.\n\n"
                f"Review summary: {summary[:500]}",
            )

            # Update snapshot
            db.upsert_snapshot(
                db.StatusSnapshot(
                    work_package_id=wp.id,
                    wp_status=new_status_name or "Done",
                    pr_number=pr_number,
                    pr_state="closed",
                    ci_conclusion="success",
                )
            )
        else:
            log.warning(
                "review.approved_but_ci_not_passing",
                pr=pr_number,
                ci=ci,
            )
            op.add_comment(
                wp.id,
                f"AI-DLC review **approved** PR #{pr_number} but CI status is "
                f"**{ci or 'unknown'}** — skipping auto-merge. "
                f"Review summary: {summary[:500]}",
            )
    else:
        # request_changes — comment on OpenProject but don't fail the batch
        op.add_comment(
            wp.id,
            f"AI-DLC review **requested changes** on PR #{pr_number}.\n\n"
            f"Review summary: {summary[:500]}",
        )

    # ---- persist -----------------------------------------------------------
    db.record_run(
        stage="review",
        work_package_id=wp.id,
        status="ok",
        pr_url=pr.url,
        notes=f"verdict={verdict} merged={merged} comments={len(comments)}",
    )

    return ReviewAndMergeResult(
        work_package_id=wp.id,
        pr_number=pr_number,
        verdict=verdict,
        summary=summary,
        merged=merged,
    )
