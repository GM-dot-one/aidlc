"""Seed a demo project + a handful of raw feature ideas into OpenProject.

Run once after `make up`:
    python scripts/seed_openproject.py

Idempotent-ish: if a project with the configured identifier already exists,
we just add ideas to it. Ideas are only created if none with a matching
subject already exist.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# Allow running as `python scripts/seed_openproject.py`
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aidlc.config import get_settings
from aidlc.openproject import OpenProjectClient
from aidlc.openproject.client import OpenProjectError

IDEAS: list[tuple[str, str]] = [
    (
        "Let accountants export the invoices list to CSV",
        "Our finance customers keep asking if they can pull the invoices list into "
        "their own BI tool. Today they screen-scrape. Ideally we add a CSV export "
        "button on the invoices page that respects the current filters.",
    ),
    (
        "Warn when BOM explosion would cause negative on-hand stock",
        "The MRP run quietly allows negative stock positions when a BOM explodes "
        "beyond available raw materials. Plant managers are asking for a hard "
        "warning (not a block) with a drill-down to which component is short.",
    ),
    (
        "Make the GL close checklist reusable across entities",
        "Each legal entity currently gets a copy of the same 40-step GL close "
        "checklist, edited in place. Consolidated customers want a master template "
        "that rolls down to entities with entity-specific overrides.",
    ),
]


def ensure_project(client: OpenProjectClient, identifier: str, name: str) -> None:
    """Create the demo project if it doesn't already exist."""
    try:
        client._get(f"/api/v3/projects/{identifier}")
        print(f"✓ project '{identifier}' already exists")
        return
    except OpenProjectError as exc:
        if exc.status_code != 404:
            raise

    body: dict[str, Any] = {
        "identifier": identifier,
        "name": name,
        "description": {
            "format": "markdown",
            "raw": "Demo project for the AI-DLC agent. Safe to delete.",
        },
    }
    client._post("/api/v3/projects", body)
    print(f"✓ created project '{identifier}'")


def seed_ideas(client: OpenProjectClient, project_identifier: str) -> None:
    feature_type = client.find_type_by_name("Feature") or client.list_types()[0]

    # Gather existing subjects so we don't double-seed.
    existing = {
        wp.subject for wp in client.list_work_packages(project_identifier=project_identifier)
    }

    for subject, description in IDEAS:
        if subject in existing:
            print(f"  · skipping existing idea '{subject}'")
            continue
        wp = client.create_work_package(
            project_identifier=project_identifier,
            subject=subject,
            description=description,
            type_id=feature_type.id,
        )
        print(f"  + created WP #{wp.id}: {subject}")


def main() -> int:
    s = get_settings()
    with OpenProjectClient(
        base_url=s.openproject_url, api_key=s.openproject_api_key.get_secret_value()
    ) as client:
        ensure_project(client, identifier=s.openproject_project, name="AI-DLC Demo")
        seed_ideas(client, project_identifier=s.openproject_project)
    print("\nDone. Try:")
    print("  aidlc doctor")
    print(
        f"  aidlc spec <wp-id>   # grab an id from http://localhost:8080/projects/{s.openproject_project}/work_packages"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
