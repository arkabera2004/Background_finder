"""Per-owner daily rate limit on new research runs.

Counts runs already created by this owner in the trailing 24h using the
existing run_store (no separate counter to keep in sync). Limit comes
from settings.max_runs_per_user_per_day (default 30, see
backend/.env.example), matching docs/SECURITY.md.
"""

from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.db.memory_store import RunStore


class RateLimitExceededError(Exception):
    def __init__(self, limit: int):
        self.limit = limit
        super().__init__(f"Daily limit of {limit} research runs exceeded")


def check_research_rate_limit(run_store: RunStore, owner_id: str, limit: int | None = None) -> None:
    effective_limit = limit if limit is not None else settings.max_runs_per_user_per_day
    cutoff = datetime.now(timezone.utc) - timedelta(days=1)
    recent = [r for r in run_store.list_for_owner(owner_id) if r.created_at >= cutoff]
    if len(recent) >= effective_limit:
        raise RateLimitExceededError(effective_limit)
