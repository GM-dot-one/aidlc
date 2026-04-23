"""HTTP-level tests for OpenProjectClient using respx to mock httpx."""

from __future__ import annotations

import base64

import httpx
import pytest
import respx

from aidlc.openproject.client import OpenProjectClient, OpenProjectError

BASE = "http://op.test"


def _client() -> OpenProjectClient:
    return OpenProjectClient(base_url=BASE, api_key="secret")


@respx.mock
def test_list_work_packages_parses_embedded_elements() -> None:
    respx.get(f"{BASE}/api/v3/projects/demo/work_packages").mock(
        return_value=httpx.Response(
            200,
            json={
                "_embedded": {
                    "elements": [
                        {
                            "id": 1,
                            "subject": "A",
                            "description": {"raw": "aa"},
                            "_links": {
                                "status": {"href": "/api/v3/statuses/1", "title": "New"},
                                "type": {"href": "/api/v3/types/2", "title": "Feature"},
                            },
                        },
                        {
                            "id": 2,
                            "subject": "B",
                            "description": {"raw": ""},
                            "_links": {},
                        },
                    ]
                }
            },
        )
    )
    with _client() as c:
        results = c.list_work_packages(project_identifier="demo")
    assert [r.id for r in results] == [1, 2]
    assert results[0].status_name == "New"
    assert results[0].type_id == 2


@respx.mock
def test_auth_header_uses_apikey_basic_scheme() -> None:
    route = respx.get(f"{BASE}/api/v3/work_packages/1").mock(
        return_value=httpx.Response(200, json={"id": 1, "subject": "x", "_links": {}})
    )
    with _client() as c:
        c.get_work_package(1)
    auth = route.calls[0].request.headers["authorization"]
    assert auth.startswith("Basic ")
    decoded = base64.b64decode(auth.removeprefix("Basic ")).decode()
    assert decoded == "apikey:secret"


@respx.mock
def test_raises_openproject_error_on_4xx() -> None:
    respx.get(f"{BASE}/api/v3/work_packages/404").mock(
        return_value=httpx.Response(404, text='{"message":"not found"}')
    )
    with _client() as c, pytest.raises(OpenProjectError) as exc_info:
        c.get_work_package(404)
    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.body


@respx.mock
def test_update_work_package_sends_lock_version_and_status_link() -> None:
    respx.get(f"{BASE}/api/v3/work_packages/5").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": 5,
                "subject": "hi",
                "description": {"raw": "orig"},
                "lockVersion": 7,
                "_links": {},
            },
        )
    )
    patch_route = respx.patch(f"{BASE}/api/v3/work_packages/5").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": 5,
                "subject": "hi",
                "description": {"raw": "new"},
                "lockVersion": 8,
                "_links": {"status": {"href": "/api/v3/statuses/3", "title": "Specified"}},
            },
        )
    )
    with _client() as c:
        wp = c.get_work_package(5)
        updated = c.update_work_package(wp, description="new", status_id=3)

    import json as _json

    call_body = _json.loads(patch_route.calls[0].request.content)
    assert call_body["lockVersion"] == 7
    assert call_body["_links"]["status"]["href"] == "/api/v3/statuses/3"
    assert updated.status_name == "Specified"


@respx.mock
def test_find_type_by_name_is_case_insensitive() -> None:
    respx.get(f"{BASE}/api/v3/types").mock(
        return_value=httpx.Response(
            200,
            json={
                "_embedded": {
                    "elements": [
                        {"id": 1, "name": "Task"},
                        {"id": 2, "name": "Feature"},
                    ]
                }
            },
        )
    )
    with _client() as c:
        t = c.find_type_by_name("feature")
    assert t is not None
    assert t.id == 2
