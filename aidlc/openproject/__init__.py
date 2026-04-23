"""OpenProject REST API v3 (HAL+JSON) adapter."""

from __future__ import annotations

from aidlc.openproject.client import OpenProjectClient, OpenProjectError
from aidlc.openproject.models import Status, Type, WorkPackage

__all__ = ["OpenProjectClient", "OpenProjectError", "Status", "Type", "WorkPackage"]
