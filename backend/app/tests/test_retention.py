from datetime import datetime, timedelta, timezone

from app.db.memory_store import RunStore
from app.services.retention import purge_expired_runs


def test_deletes_runs_older_than_cutoff():
    store = RunStore()
    old_run = store.create(owner_id="user-1", depth="standard")
    old_run.created_at = datetime.now(timezone.utc) - timedelta(days=91)

    deleted = purge_expired_runs(store, days=90)

    assert deleted == 1
    assert store.get(old_run.id, "user-1") is None


def test_keeps_runs_within_window():
    store = RunStore()
    recent_run = store.create(owner_id="user-1", depth="standard")
    recent_run.created_at = datetime.now(timezone.utc) - timedelta(days=5)

    deleted = purge_expired_runs(store, days=90)

    assert deleted == 0
    assert store.get(recent_run.id, "user-1") is not None


def test_mixed_batch_only_deletes_expired():
    store = RunStore()
    old_run = store.create(owner_id="user-1", depth="standard")
    old_run.created_at = datetime.now(timezone.utc) - timedelta(days=100)
    recent_run = store.create(owner_id="user-1", depth="standard")

    deleted = purge_expired_runs(store, days=90)

    assert deleted == 1
    assert store.get(old_run.id, "user-1") is None
    assert store.get(recent_run.id, "user-1") is not None


def test_purges_across_owners():
    store = RunStore()
    run_a = store.create(owner_id="user-a", depth="standard")
    run_a.created_at = datetime.now(timezone.utc) - timedelta(days=91)
    run_b = store.create(owner_id="user-b", depth="standard")
    run_b.created_at = datetime.now(timezone.utc) - timedelta(days=91)

    deleted = purge_expired_runs(store, days=90)

    assert deleted == 2
