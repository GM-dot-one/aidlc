"""HTTP-level tests for GitHubClient."""

from __future__ import annotations

import httpx
import respx

from aidlc.git_host import GitHubClient

BASE = "https://api.github.com"
REPO = "acme/repo"


def _client() -> GitHubClient:
    return GitHubClient(token="tok", repo=REPO)


@respx.mock
def test_get_branch_sha() -> None:
    respx.get(f"{BASE}/repos/{REPO}/git/ref/heads/main").mock(
        return_value=httpx.Response(200, json={"object": {"sha": "deadbeef"}})
    )
    with _client() as c:
        assert c.get_branch_sha("main") == "deadbeef"


@respx.mock
def test_commit_file_creates_when_missing() -> None:
    respx.get(f"{BASE}/repos/{REPO}/contents/x.py").mock(
        return_value=httpx.Response(404, text='{"message":"Not Found"}')
    )
    put_route = respx.put(f"{BASE}/repos/{REPO}/contents/x.py").mock(
        return_value=httpx.Response(
            201,
            json={"commit": {"sha": "newsha"}, "content": {"sha": "blobsha"}},
        )
    )
    with _client() as c:
        sha = c.commit_file(branch="feat/x", path="x.py", content="print(1)\n", message="m")
    assert sha == "newsha"
    import json as _json

    body = _json.loads(put_route.calls[0].request.content)
    assert body["branch"] == "feat/x"
    # File didn't exist, so we must NOT have sent a blob sha
    assert "sha" not in body


@respx.mock
def test_ci_conclusion_aggregation() -> None:
    def check_runs(conclusions: list[str | None]) -> dict:
        return {"check_runs": [{"conclusion": c} for c in conclusions]}

    # No runs at all
    respx.get(f"{BASE}/repos/{REPO}/commits/a/check-runs").mock(
        return_value=httpx.Response(200, json={"check_runs": []})
    )
    # All success
    respx.get(f"{BASE}/repos/{REPO}/commits/b/check-runs").mock(
        return_value=httpx.Response(200, json=check_runs(["success", "skipped"]))
    )
    # One failure
    respx.get(f"{BASE}/repos/{REPO}/commits/c/check-runs").mock(
        return_value=httpx.Response(200, json=check_runs(["success", "failure"]))
    )
    # Still running
    respx.get(f"{BASE}/repos/{REPO}/commits/d/check-runs").mock(
        return_value=httpx.Response(200, json=check_runs(["success", None]))
    )
    with _client() as c:
        assert c.ci_conclusion("a") is None
        assert c.ci_conclusion("b") == "success"
        assert c.ci_conclusion("c") == "failure"
        assert c.ci_conclusion("d") == "pending"


@respx.mock
def test_open_pull_request_returns_dataclass() -> None:
    respx.post(f"{BASE}/repos/{REPO}/pulls").mock(
        return_value=httpx.Response(
            201,
            json={
                "number": 42,
                "html_url": "https://github.com/acme/repo/pull/42",
                "head": {"sha": "headsha"},
                "state": "open",
                "merged": False,
            },
        )
    )
    with _client() as c:
        pr = c.open_pull_request(title="t", body="b", head="feat/x", base="main", draft=True)
    assert pr.number == 42
    assert pr.state == "open"
    assert pr.merged is False
