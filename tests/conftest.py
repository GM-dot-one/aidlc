"""Pytest fixtures.

Every test gets:
- A temp SQLite DB (so ``db.has_run`` etc. behave deterministically).
- Env vars set so ``Settings()`` constructs without real secrets.
- Fresh singleton caches between tests.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest

# Set env BEFORE importing aidlc.config — pydantic-settings reads at class-body time.
os.environ.setdefault("OPENPROJECT_API_KEY", "test-op-key")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")
os.environ.setdefault("GITHUB_TOKEN", "test-gh-token")
os.environ.setdefault("GITHUB_REPO", "acme/repo")
os.environ.setdefault("OPENPROJECT_URL", "http://op.test")


@pytest.fixture(autouse=True)
def _tmp_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Point the agent at a per-test SQLite DB."""
    db_path = tmp_path / "state.db"
    monkeypatch.setenv("AIDLC_DB_PATH", str(db_path))

    from aidlc import db as db_mod
    from aidlc.config import get_settings

    get_settings.cache_clear()
    db_mod.reset_engine()
    yield db_path
    db_mod.reset_engine()
    get_settings.cache_clear()
