from datetime import datetime, timedelta, timezone

from app.core.config import settings
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


def test_default_days_comes_from_settings(monkeypatch):
    monkeypatch.setattr(settings, "default_retention_days", 5)
    store = RunStore()
    run = store.create(owner_id="user-1", depth="standard")
    run.created_at = datetime.now(timezone.utc) - timedelta(days=6)

    deleted = purge_expired_runs(store)  # no explicit days passed

    assert deleted == 1


def test_chanakya_retention_sweep_purges_old_runs(monkeypatch):
    from sqlalchemy.orm import sessionmaker

    from app.db.chanakya_repository import ChanakyaRunRepository
    from app.db.session import init_db, make_engine

    engine = make_engine("sqlite:///:memory:")
    init_db(bind=engine)
    session = sessionmaker(bind=engine)()
    repo = ChanakyaRunRepository(session)
    old_run = repo.create_run("user-1", "2026-01")
    old_run.created_at = datetime.now(timezone.utc) - timedelta(days=100)
    recent_run = repo.create_run("user-1", "2026-11")
    session.commit()

    monkeypatch.setattr("app.db.session.get_session", lambda: session)

    import importlib

    workers_main = importlib.import_module("app.workers.main")
    monkeypatch.setattr(workers_main, "get_session", lambda: session)

    import asyncio

    old_run_id, recent_run_id = old_run.id, recent_run.id
    result = asyncio.run(workers_main.run_retention_sweep(ctx={}))

    verify_session = sessionmaker(bind=engine)()
    verify_repo = ChanakyaRunRepository(verify_session)
    assert result["chanakya_deleted"] == 1
    assert verify_repo.get(old_run_id, "user-1") is None
    assert verify_repo.get(recent_run_id, "user-1") is not None
    verify_session.close()
