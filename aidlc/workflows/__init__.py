"""The four AI-DLC workflow stages.

Each stage is a pure function that takes its dependencies explicitly
(LLM, OpenProject client, optionally GitHub client) so tests can inject
fakes without monkey-patching.
"""

from __future__ import annotations

from aidlc.workflows.code_all_local import run_code_all_local
from aidlc.workflows.idea_to_spec import run_idea_to_spec
from aidlc.workflows.review_all import run_review_all
from aidlc.workflows.review_and_merge import run_review_and_merge
from aidlc.workflows.spec_to_tasks import run_spec_to_tasks
from aidlc.workflows.status_updates import run_status_updates
from aidlc.workflows.task_to_code import run_task_to_code
from aidlc.workflows.task_to_code_local import run_task_to_code_local

__all__ = [
    "run_code_all_local",
    "run_idea_to_spec",
    "run_review_all",
    "run_review_and_merge",
    "run_spec_to_tasks",
    "run_status_updates",
    "run_task_to_code",
    "run_task_to_code_local",
]
