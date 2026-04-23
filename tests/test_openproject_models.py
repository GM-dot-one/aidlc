"""Verify the HAL→flat transformation on OpenProject's work package payload."""

from __future__ import annotations

from aidlc.openproject.models import WorkPackage

HAL_FIXTURE = {
    "id": 1234,
    "subject": "Add CSV export to invoices list",
    "description": {"format": "markdown", "raw": "Accountants need to export invoices."},
    "lockVersion": 3,
    "_links": {
        "self": {"href": "/api/v3/work_packages/1234"},
        "status": {"href": "/api/v3/statuses/7", "title": "New"},
        "type": {"href": "/api/v3/types/2", "title": "Feature"},
        "project": {"href": "/api/v3/projects/ai-dlc-demo", "title": "AI-DLC Demo"},
        "parent": {"href": "/api/v3/work_packages/999"},
    },
}


class TestWorkPackageFromHal:
    def test_flattens_basic_fields(self) -> None:
        wp = WorkPackage.from_hal(HAL_FIXTURE)
        assert wp.id == 1234
        assert wp.subject == "Add CSV export to invoices list"
        assert wp.description_text == "Accountants need to export invoices."
        assert wp.lock_version == 3

    def test_pulls_status_from_links(self) -> None:
        wp = WorkPackage.from_hal(HAL_FIXTURE)
        assert wp.status_id == 7
        assert wp.status_name == "New"

    def test_pulls_type_from_links(self) -> None:
        wp = WorkPackage.from_hal(HAL_FIXTURE)
        assert wp.type_id == 2
        assert wp.type_name == "Feature"

    def test_pulls_parent_id(self) -> None:
        wp = WorkPackage.from_hal(HAL_FIXTURE)
        assert wp.parent_id == 999

    def test_pulls_project_identifier(self) -> None:
        wp = WorkPackage.from_hal(HAL_FIXTURE)
        assert wp.project_identifier == "ai-dlc-demo"

    def test_survives_missing_links(self) -> None:
        minimal = {"id": 1, "subject": "x"}
        wp = WorkPackage.from_hal(minimal)
        assert wp.id == 1
        assert wp.status_id is None
        assert wp.parent_id is None
