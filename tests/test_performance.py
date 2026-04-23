"""Tests for performance optimizations."""

from __future__ import annotations

import httpx
import respx

from aidlc.openproject.client import OpenProjectClient


class TestMetadataCaching:
    """Verify that list_types/list_statuses use the TTL cache."""

    def _make_client(self) -> OpenProjectClient:
        return OpenProjectClient(
            base_url="http://op.test",
            api_key="test-key",
            client=httpx.Client(
                transport=respx.mock(assert_all_called=False),
                headers={"Authorization": "Basic dGVzdA=="},
            ),
        )

    @respx.mock
    def test_list_types_caches_result(self) -> None:
        types_response = {
            "_embedded": {
                "elements": [
                    {"id": 1, "name": "Task"},
                    {"id": 2, "name": "Feature"},
                ]
            }
        }
        route = respx.get("http://op.test/api/v3/types").mock(
            return_value=httpx.Response(200, json=types_response)
        )

        client = OpenProjectClient(
            base_url="http://op.test",
            api_key="test-key",
        )

        result1 = client.list_types()
        result2 = client.list_types()

        assert len(result1) == 2
        assert len(result2) == 2
        assert route.call_count == 1

    @respx.mock
    def test_list_statuses_caches_result(self) -> None:
        statuses_response = {
            "_embedded": {
                "elements": [
                    {"id": 1, "name": "New", "isClosed": False},
                    {"id": 2, "name": "Closed", "isClosed": True},
                ]
            }
        }
        route = respx.get("http://op.test/api/v3/statuses").mock(
            return_value=httpx.Response(200, json=statuses_response)
        )

        client = OpenProjectClient(
            base_url="http://op.test",
            api_key="test-key",
        )

        result1 = client.list_statuses()
        result2 = client.list_statuses()

        assert len(result1) == 2
        assert len(result2) == 2
        assert route.call_count == 1

    @respx.mock
    def test_invalidate_metadata_cache_forces_refetch(self) -> None:
        types_response = {"_embedded": {"elements": [{"id": 1, "name": "Task"}]}}
        route = respx.get("http://op.test/api/v3/types").mock(
            return_value=httpx.Response(200, json=types_response)
        )

        client = OpenProjectClient(
            base_url="http://op.test",
            api_key="test-key",
        )

        client.list_types()
        assert route.call_count == 1

        client.invalidate_metadata_cache()
        client.list_types()
        assert route.call_count == 2

    @respx.mock
    def test_find_type_by_name_uses_cached_types(self) -> None:
        types_response = {
            "_embedded": {
                "elements": [
                    {"id": 1, "name": "Task"},
                    {"id": 2, "name": "Feature"},
                ]
            }
        }
        route = respx.get("http://op.test/api/v3/types").mock(
            return_value=httpx.Response(200, json=types_response)
        )

        client = OpenProjectClient(
            base_url="http://op.test",
            api_key="test-key",
        )

        t1 = client.find_type_by_name("Task")
        t2 = client.find_type_by_name("Feature")
        t3 = client.find_type_by_name("Task")

        assert t1 is not None and t1.name == "Task"
        assert t2 is not None and t2.name == "Feature"
        assert t3 is not None and t3.name == "Task"
        assert route.call_count == 1


class TestConcurrentStatusPolling:
    """Verify that status polling uses concurrent fetches."""

    def test_concurrent_polling_fetches_all_snapshots(self) -> None:
        from aidlc import db
        from aidlc.workflows.status_updates import run_status_updates
        from tests.fakes import FakeGitHub, FakeOpenProject

        op = FakeOpenProject()
        gh = FakeGitHub()

        for i in range(3):
            task = op.add_wp(subject=f"task-{i}", type_name="Task")
            gh.branches[f"aidlc/t{i}"] = f"sha{i}"
            pr = gh.open_pull_request(title=f"t{i}", body="b", head=f"aidlc/t{i}", base="main")
            gh.ci_by_sha[f"sha{i}"] = None
            db.upsert_snapshot(
                db.StatusSnapshot(
                    work_package_id=task.id,
                    wp_status="New",
                    pr_number=pr.number,
                    pr_state="open",
                    ci_conclusion=None,
                )
            )

        changes = run_status_updates(op=op, gh=gh)
        assert len(changes) == 3
        assert all(c.transition == "no_change" for c in changes)


class TestSQLiteWALMode:
    """Verify that SQLite WAL mode is enabled."""

    def test_wal_mode_enabled(self) -> None:
        from sqlalchemy import text

        from aidlc.db import get_engine

        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA journal_mode")).scalar()
            assert result == "wal"
