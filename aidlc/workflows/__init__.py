"""The four AI-DLC workflow stages.

Each stage is a pure function that takes its dependencies explicitly
(LLM, OpenProject client, optionally GitHub client) so tests can inject
fakes without monkey-patching.
"""

from __future__ import annotations

from aidlc.workflows.idea_to_spec import run_idea_to_spec
from aidlc.workflows.spec_to_tasks import run_spec_to_tasks
from aidlc.workflows.status_updates import run_status_updates
from aidlc.workflows.task_to_code import run_task_to_code

__all__ = [
    "run_idea_to_spec",
    "run_spec_to_tasks",
    "run_status_updates",
    "run_task_to_code",
]
