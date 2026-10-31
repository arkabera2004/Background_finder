"""90-day retention for research Runs.

Scope: unsaved research Runs only. A Run is throwaway working state; the
explicit domain decision (see app/db/models.py) is that a Prospect is a
separate, user-initiated save that survives independently of its
originating Run — retention never touches Prospects or Briefs.
"""

from datetime import datetime, timedelta, timezone

from app.db.memory_store import RunStore

RETENTION_DAYS = 90


def purge_expired_runs(run_store: RunStore, days: int = RETENTION_DAYS) -> int:
    """Delete Runs older than `days`. Returns the number deleted."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    expired = [r.id for r in run_store.list_all() if r.created_at < cutoff]
    for run_id in expired:
        run_store.delete(run_id)
    return len(expired)
