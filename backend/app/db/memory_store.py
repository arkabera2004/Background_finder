"""In-memory persistence used until a real Supabase project exists.

This is NOT a mock standing in for a provider — it is the actual storage
backend for research runs today. It will be swapped for a Supabase-backed
repository with the same interface once credentials exist; the interface
(create/get/update run, append step, list) is designed so that swap doesn't
touch calling code.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class RunStep:
    stage: str
    status: str = "pending"  # pending | running | completed | failed
    output: dict[str, Any] | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


@dataclass
class Run:
    id: str
    owner_id: str
    depth: str
    status: str = "pending"  # pending | running | completed | failed | cancelled
    steps: dict[str, RunStep] = field(default_factory=dict)
    brief: dict[str, Any] | None = None
    sources: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    cancel_requested: bool = False


class RunStore:
    """Process-local run store. Not multi-process safe — fine for one dev server."""

    def __init__(self):
        self._runs: dict[str, Run] = {}

    def create(self, owner_id: str, depth: str) -> Run:
        run = Run(id=str(uuid.uuid4()), owner_id=owner_id, depth=depth)
        self._runs[run.id] = run
        return run

    def get(self, run_id: str, owner_id: str) -> Run | None:
        run = self._runs.get(run_id)
        if run is None or run.owner_id != owner_id:
            return None
        return run

    def list_for_owner(self, owner_id: str) -> list[Run]:
        return [r for r in self._runs.values() if r.owner_id == owner_id]


run_store = RunStore()
