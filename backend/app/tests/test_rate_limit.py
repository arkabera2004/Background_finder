from datetime import datetime, timedelta, timezone

import pytest

from app.core.config import settings
from app.db.memory_store import RunStore
from app.services.rate_limit import RateLimitExceededError, check_research_rate_limit


def test_allows_runs_under_limit():
    store = RunStore()
    for _ in range(5):
        store.create(owner_id="user-1", depth="standard")

    check_research_rate_limit(store, "user-1", limit=30)  # should not raise


def test_blocks_at_limit():
    store = RunStore()
    for _ in range(3):
        store.create(owner_id="user-1", depth="standard")

    with pytest.raises(RateLimitExceededError):
        check_research_rate_limit(store, "user-1", limit=3)


def test_old_runs_dont_count_toward_limit():
    store = RunStore()
    old_run = store.create(owner_id="user-1", depth="standard")
    old_run.created_at = datetime.now(timezone.utc) - timedelta(days=2)

    check_research_rate_limit(store, "user-1", limit=1)  # only the old run exists, shouldn't block


def test_limit_is_per_owner():
    store = RunStore()
    for _ in range(5):
        store.create(owner_id="user-1", depth="standard")

    check_research_rate_limit(store, "user-2", limit=1)  # different owner, unaffected


def test_default_limit_comes_from_settings(monkeypatch):
    monkeypatch.setattr(settings, "max_runs_per_user_per_day", 2)
    store = RunStore()
    for _ in range(2):
        store.create(owner_id="user-1", depth="standard")

    with pytest.raises(RateLimitExceededError) as exc_info:
        check_research_rate_limit(store, "user-1")  # no explicit limit passed

    assert exc_info.value.limit == 2
