"""OpenProject API v3 client.

OpenProject API reference: https://www.openproject.org/docs/api/

Authentication: HTTP Basic with user "apikey" and the API token as password.
All responses are HAL+JSON. Writes send plain JSON and include ``lockVersion``
for optimistic concurrency.

We keep this client focused on the endpoints the AI-DLC workflows actually
call. Widen deliberately, not speculatively.
"""

from __future__ import annotations

import base64
from typing import Any

import httpx
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from aidlc.logging import get_logger
from aidlc.openproject.models import Status, Type, WorkPackage

log = get_logger(__name__)


class OpenProjectError(RuntimeError):
    """Raised on any non-2xx response, carries status + body for debugging."""

    def __init__(self, status_code: int, body: str, url: str) -> None:
        super().__init__(f"OpenProject {status_code} on {url}: {body[:300]}")
        self.status_code = status_code
        self.body = body
        self.url = url


_RETRYABLE = (httpx.TransportError, httpx.ReadTimeout, httpx.ConnectError)


class OpenProjectClient:
    """Thin typed wrapper around OpenProject's REST API v3."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        timeout: float = 15.0,
        client: httpx.Client | None = None,
    ) -> None:
        self._base = base_url.rstrip("/")
        token = base64.b64encode(f"apikey:{api_key}".encode()).decode()
        self._headers = {
            "Authorization": f"Basic {token}",
            "Accept": "application/hal+json",
            "Content-Type": "application/json",
        }
        self._client = client or httpx.Client(timeout=timeout, headers=self._headers)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> OpenProjectClient:
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    # ---- low-level ---------------------------------------------------------

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
        retry=retry_if_exception_type(_RETRYABLE),
    )
    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        url = f"{self._base}{path}"
        log.debug("op.request", method=method, path=path)
        response = self._client.request(method, url, headers=self._headers, **kwargs)
        if response.status_code >= 400:
            raise OpenProjectError(response.status_code, response.text, url)
        return response

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        data: dict[str, Any] = self._request("GET", path, params=params).json()
        return data

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        data: dict[str, Any] = self._request("POST", path, json=body).json()
        return data

    def _patch(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        data: dict[str, Any] = self._request("PATCH", path, json=body).json()
        return data

    # ---- work packages -----------------------------------------------------

    def list_work_packages(
        self,
        *,
        project_identifier: str,
        filters: list[dict[str, Any]] | None = None,
        page_size: int = 50,
    ) -> list[WorkPackage]:
        """List work packages in a project. ``filters`` follows OP's filter DSL.

        Example filter — only ready (New) tasks:
            [{"status": {"operator": "=", "values": ["1"]}}]
        """
        import json as _json

        params: dict[str, Any] = {"pageSize": page_size}
        if filters:
            params["filters"] = _json.dumps(filters)
        payload = self._get(f"/api/v3/projects/{project_identifier}/work_packages", params)
        elements = (payload.get("_embedded") or {}).get("elements", [])
        return [WorkPackage.from_hal(el) for el in elements]

    def get_work_package(self, wp_id: int) -> WorkPackage:
        return WorkPackage.from_hal(self._get(f"/api/v3/work_packages/{wp_id}"))

    def create_work_package(
        self,
        *,
        project_identifier: str,
        subject: str,
        description: str,
        type_id: int,
        parent_id: int | None = None,
    ) -> WorkPackage:
        body: dict[str, Any] = {
            "subject": subject,
            "description": {"format": "markdown", "raw": description},
            "_links": {
                "type": {"href": f"/api/v3/types/{type_id}"},
            },
        }
        if parent_id is not None:
            body["_links"]["parent"] = {"href": f"/api/v3/work_packages/{parent_id}"}
        payload = self._post(
            f"/api/v3/projects/{project_identifier}/work_packages",
            body,
        )
        return WorkPackage.from_hal(payload)

    def update_work_package(
        self,
        wp: WorkPackage,
        *,
        description: str | None = None,
        status_id: int | None = None,
        subject: str | None = None,
    ) -> WorkPackage:
        """Patch selected fields. Pass the original ``WorkPackage`` for ``lockVersion``."""
        body: dict[str, Any] = {"lockVersion": wp.lock_version, "_links": {}}
        if description is not None:
            body["description"] = {"format": "markdown", "raw": description}
        if subject is not None:
            body["subject"] = subject
        if status_id is not None:
            body["_links"]["status"] = {"href": f"/api/v3/statuses/{status_id}"}
        if not body["_links"]:
            body.pop("_links")
        payload = self._patch(f"/api/v3/work_packages/{wp.id}", body)
        return WorkPackage.from_hal(payload)

    def add_comment(self, wp_id: int, markdown: str) -> None:
        body = {"comment": {"format": "markdown", "raw": markdown}}
        self._post(f"/api/v3/work_packages/{wp_id}/activities", body)

    # ---- metadata ----------------------------------------------------------

    def list_types(self) -> list[Type]:
        payload = self._get("/api/v3/types")
        return [
            Type(id=el["id"], name=el["name"])
            for el in (payload.get("_embedded") or {}).get("elements", [])
        ]

    def list_statuses(self) -> list[Status]:
        payload = self._get("/api/v3/statuses")
        return [
            Status(id=el["id"], name=el["name"], isClosed=el.get("isClosed", False))
            for el in (payload.get("_embedded") or {}).get("elements", [])
        ]

    def find_type_by_name(self, name: str) -> Type | None:
        for t in self.list_types():
            if t.name.lower() == name.lower():
                return t
        return None

    def find_status_by_name(self, name: str) -> Status | None:
        for s in self.list_statuses():
            if s.name.lower() == name.lower():
                return s
        return None


__all__ = ["OpenProjectClient", "OpenProjectError", "RetryError"]
