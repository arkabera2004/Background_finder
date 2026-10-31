"""90-day retention for research Runs.

Scope: unsaved research Runs only. A Run is throwaway working state; the
explicit domain decision (see app/db/models.py) is that a Prospect is a
separate, user-initiated save that survives independently of its
originating Run — retention never touches Prospects or Briefs.
"""

from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.db.memory_store import RunStore


def purge_expired_runs(run_store: RunStore, days: int | None = None) -> int:
    """Delete Runs older than `days` (defaults to settings.default_retention_days).
    Returns the number deleted."""
    effective_days = days if days is not None else settings.default_retention_days
    cutoff = datetime.now(timezone.utc) - timedelta(days=effective_days)
    expired = [r.id for r in run_store.list_all() if r.created_at < cutoff]
    for run_id in expired:
        run_store.delete(run_id)
    return len(expired)
