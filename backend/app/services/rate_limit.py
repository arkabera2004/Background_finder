"""Per-owner daily rate limit on new research runs.

Counts runs already created by this owner in the trailing 24h using the
existing run_store (no separate counter to keep in sync). Free Basic Plan
limit: 30 runs/day, matching docs/SECURITY.md.
"""

from datetime import datetime, timedelta, timezone

from app.db.memory_store import RunStore

DAILY_RUN_LIMIT = 30


class RateLimitExceededError(Exception):
    def __init__(self, limit: int):
        self.limit = limit
        super().__init__(f"Daily limit of {limit} research runs exceeded")


def check_research_rate_limit(run_store: RunStore, owner_id: str, limit: int = DAILY_RUN_LIMIT) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=1)
    recent = [r for r in run_store.list_for_owner(owner_id) if r.created_at >= cutoff]
    if len(recent) >= limit:
        raise RateLimitExceededError(limit)
