"""Minimal GitHub REST v3 client.

We deliberately avoid PyGithub / ghapi because (a) we need only a handful of
endpoints and (b) a hand-rolled adapter keeps the retry/error surface
consistent with ``OpenProjectClient``.

Endpoints we exercise:
  - GET   /repos/{owner}/{repo}
  - GET   /repos/{owner}/{repo}/git/ref/heads/{branch}       (get base sha)
  - POST  /repos/{owner}/{repo}/git/refs                     (create branch)
  - PUT   /repos/{owner}/{repo}/contents/{path}              (commit a file)
  - POST  /repos/{owner}/{repo}/pulls                        (open PR)
  - GET   /repos/{owner}/{repo}/pulls/{number}               (poll PR state)
  - GET   /repos/{owner}/{repo}/pulls/{number}               (diff, via Accept header)
  - POST  /repos/{owner}/{repo}/pulls/{number}/reviews       (submit review)
  - PUT   /repos/{owner}/{repo}/pulls/{number}/merge         (merge PR)
  - PUT   /repos/{owner}/{repo}/pulls/{number}/update-branch (update branch)
  - GET   /repos/{owner}/{repo}/commits/{sha}/check-runs     (CI conclusion)
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from aidlc.logging import get_logger

log = get_logger(__name__)

_RETRYABLE = (httpx.TransportError, httpx.ReadTimeout, httpx.ConnectError)


class GitHubError(RuntimeError):
    def __init__(self, status_code: int, body: str, url: str) -> None:
        super().__init__(f"GitHub {status_code} on {url}: {body[:300]}")
        self.status_code = status_code
        self.body = body
        self.url = url


@dataclass
class PullRequest:
    number: int
    url: str
    head_sha: str
    state: str  # open | closed
    merged: bool


class GitHubClient:
    """Tiny REST client scoped to a single ``owner/repo``."""

    BASE = "https://api.github.com"

    def __init__(
        self,
        *,
        token: str,
        repo: str,
        client: httpx.Client | None = None,
        timeout: float = 15.0,
    ) -> None:
        if "/" not in repo:
            raise ValueError("repo must be 'owner/name'")
        self._repo = repo
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "aidlc-agent",
        }
        self._client = client or httpx.Client(timeout=timeout, headers=self._headers)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> GitHubClient:
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
        retry=retry_if_exception_type(_RETRYABLE),
    )
    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        url = f"{self.BASE}{path}"
        log.debug("gh.request", method=method, path=path)
        response = self._client.request(method, url, headers=self._headers, **kwargs)
        if response.status_code >= 400:
            raise GitHubError(response.status_code, response.text, url)
        return response

    # ---- branching & commits ----------------------------------------------

    def get_branch_sha(self, branch: str) -> str:
        payload = self._request("GET", f"/repos/{self._repo}/git/ref/heads/{branch}").json()
        return str(payload["object"]["sha"])

    def create_branch(self, *, new_branch: str, from_sha: str) -> None:
        body = {"ref": f"refs/heads/{new_branch}", "sha": from_sha}
        self._request("POST", f"/repos/{self._repo}/git/refs", json=body)

    def commit_file(
        self,
        *,
        branch: str,
        path: str,
        content: str,
        message: str,
    ) -> str:
        """Create or update a single file on ``branch``. Returns the new commit sha."""
        encoded = base64.b64encode(content.encode()).decode()
        body: dict[str, Any] = {
            "message": message,
            "content": encoded,
            "branch": branch,
        }
        # If file already exists we need its blob sha to update it.
        try:
            existing = self._request(
                "GET", f"/repos/{self._repo}/contents/{path}", params={"ref": branch}
            ).json()
            if isinstance(existing, dict) and "sha" in existing:
                body["sha"] = existing["sha"]
        except GitHubError as exc:
            if exc.status_code != 404:
                raise
        payload = self._request("PUT", f"/repos/{self._repo}/contents/{path}", json=body).json()
        return str(payload["commit"]["sha"])

    # ---- pull requests -----------------------------------------------------

    def open_pull_request(
        self,
        *,
        title: str,
        body: str,
        head: str,
        base: str,
        draft: bool = False,
    ) -> PullRequest:
        payload = self._request(
            "POST",
            f"/repos/{self._repo}/pulls",
            json={"title": title, "body": body, "head": head, "base": base, "draft": draft},
        ).json()
        return PullRequest(
            number=payload["number"],
            url=payload["html_url"],
            head_sha=payload["head"]["sha"],
            state=payload["state"],
            merged=bool(payload.get("merged", False)),
        )

    def get_pull_request(self, number: int) -> PullRequest:
        payload = self._request("GET", f"/repos/{self._repo}/pulls/{number}").json()
        return PullRequest(
            number=payload["number"],
            url=payload["html_url"],
            head_sha=payload["head"]["sha"],
            state=payload["state"],
            merged=bool(payload.get("merged", False)),
        )

    # ---- reviews & merging --------------------------------------------------

    def get_pull_request_diff(self, number: int) -> str:
        """Fetch the unified diff for a pull request."""
        url = f"{self.BASE}/repos/{self._repo}/pulls/{number}"
        log.debug("gh.request", method="GET", path=f"/repos/{self._repo}/pulls/{number}")
        headers = {**self._headers, "Accept": "application/vnd.github.diff"}
        response = self._client.request("GET", url, headers=headers)
        if response.status_code >= 400:
            raise GitHubError(response.status_code, response.text, url)
        return response.text

    def create_review(
        self,
        number: int,
        body: str,
        event: str,
        comments: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        """Submit a pull request review.

        ``event`` should be ``"APPROVE"`` or ``"REQUEST_CHANGES"``.
        ``comments`` is an optional list of ``{"path": ..., "line": ..., "body": ...}``
        dicts for inline review comments.
        """
        payload: dict[str, object] = {"body": body, "event": event}
        if comments:
            payload["comments"] = comments
        resp = self._request("POST", f"/repos/{self._repo}/pulls/{number}/reviews", json=payload)
        return resp.json()  # type: ignore[no-any-return]

    def merge_pull_request(self, number: int, merge_method: str = "squash") -> dict[str, object]:
        """Merge a pull request via the REST API."""
        resp = self._request(
            "PUT",
            f"/repos/{self._repo}/pulls/{number}/merge",
            json={"merge_method": merge_method},
        )
        return resp.json()  # type: ignore[no-any-return]

    def update_pull_request_branch(self, number: int) -> dict[str, object]:
        """Update a pull request branch with the latest base branch.

        Equivalent to clicking "Update branch" in the GitHub UI.
        """
        resp = self._request(
            "PUT",
            f"/repos/{self._repo}/pulls/{number}/update-branch",
        )
        return resp.json()  # type: ignore[no-any-return]

    # ---- CI ----------------------------------------------------------------

    def ci_conclusion(self, sha: str) -> str | None:
        """Aggregate check-runs for a commit.

        Returns:
          - "success" if all check runs concluded with success
          - "failure" if any concluded with failure/cancelled/timed_out
          - "pending" if any are still running
          - None if no check runs exist yet
        """
        payload = self._request("GET", f"/repos/{self._repo}/commits/{sha}/check-runs").json()
        runs = payload.get("check_runs", [])
        if not runs:
            return None
        conclusions = [r.get("conclusion") for r in runs]
        if any(c is None for c in conclusions):
            return "pending"
        if any(c in {"failure", "cancelled", "timed_out"} for c in conclusions):
            return "failure"
        if all(c in {"success", "neutral", "skipped"} for c in conclusions):
            return "success"
        return "pending"
