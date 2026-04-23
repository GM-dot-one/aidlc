"""Pydantic models for the subset of OpenProject's HAL+JSON we consume.

OpenProject's API v3 is deeply HAL-encoded — every resource embeds a
``_links`` map pointing at related resources. We flatten just the fields
we actually use so that the rest of the codebase can stay ignorant of HAL.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class _HAL(BaseModel):
    """Base with permissive config — OpenProject adds fields freely."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class Status(_HAL):
    id: int
    name: str
    is_closed: bool = Field(alias="isClosed", default=False)


class Type(_HAL):
    id: int
    name: str  # e.g. "Task", "Feature", "User story", "Bug", "Epic"


class Project(_HAL):
    id: int
    identifier: str
    name: str


class WorkPackage(_HAL):
    """The main unit of work in OpenProject (analogue of a Jira issue)."""

    id: int
    subject: str
    description_text: str | None = None
    status_id: int | None = None
    status_name: str | None = None
    type_id: int | None = None
    type_name: str | None = None
    project_id: int | None = None
    project_identifier: str | None = None
    parent_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    lock_version: int = 0
    raw: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_hal(cls, payload: dict[str, Any]) -> WorkPackage:
        """Parse a HAL+JSON work package resource into a flat model.

        OpenProject embeds link metadata under ``_links``; href values look
        like ``/api/v3/statuses/7`` so we pull the trailing segment as the id.
        """
        links = payload.get("_links", {}) or {}

        def _linked_id(key: str) -> int | None:
            href = (links.get(key) or {}).get("href")
            if not href:
                return None
            try:
                return int(href.rsplit("/", 1)[-1])
            except ValueError:
                return None

        def _linked_title(key: str) -> str | None:
            return (links.get(key) or {}).get("title")

        description = payload.get("description") or {}
        parent_href = ((links.get("parent") or {}).get("href")) or ""
        try:
            parent_id = int(parent_href.rsplit("/", 1)[-1]) if parent_href else None
        except ValueError:
            parent_id = None

        project_href = ((links.get("project") or {}).get("href")) or ""
        project_identifier: str | None = None
        if project_href:
            # hrefs can be /api/v3/projects/{identifier} or /projects/{id}
            project_identifier = project_href.rsplit("/", 1)[-1]

        return cls(
            id=payload["id"],
            subject=payload.get("subject", ""),
            description_text=description.get("raw"),
            status_id=_linked_id("status"),
            status_name=_linked_title("status"),
            type_id=_linked_id("type"),
            type_name=_linked_title("type"),
            project_id=_linked_id("project"),
            project_identifier=project_identifier,
            parent_id=parent_id,
            created_at=payload.get("createdAt"),
            updated_at=payload.get("updatedAt"),
            lock_version=payload.get("lockVersion", 0),
            raw=payload,
        )
