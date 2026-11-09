"""Verifies the Chanakya schema against a REAL PostgreSQL instance, not just
SQLite. Skipped automatically if no Postgres is reachable (set
TEST_POSTGRES_URL to opt in, e.g. postgresql+psycopg://user@localhost/prospectlens_test).

Covers: schema creation via Base.metadata.create_all (the same path used in
production, no Alembic), tenant isolation via owner_id filtering, concurrent
writes from two sessions, transaction rollback, index presence, and cascade
delete on retention purge.
"""

import os
import threading

import pytest
from sqlalchemy import inspect
from sqlalchemy.orm import sessionmaker

from app.db.chanakya_models import AgentExecution, MonthlyRun
from app.db.chanakya_repository import ChanakyaRunRepository
from app.db.models import Base
from app.db.session import make_engine

PG_URL = os.environ.get("TEST_POSTGRES_URL")

pytestmark = pytest.mark.skipif(
    not PG_URL, reason="set TEST_POSTGRES_URL to run tests against a real Postgres instance"
)


@pytest.fixture()
def pg_session():
    engine = make_engine(PG_URL)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_schema_creates_all_tables_on_postgres(pg_session):
    inspector = inspect(pg_session.bind)
    tables = set(inspector.get_table_names())
    assert {"chanakya_runs", "chanakya_agent_executions", "companies", "prospects"} <= tables


def test_owner_id_indexes_exist_on_postgres(pg_session):
    inspector = inspect(pg_session.bind)
    indexed_cols = {ix["column_names"][0] for ix in inspector.get_indexes("chanakya_runs")}
    assert "owner_id" in indexed_cols


def test_tenant_isolation_on_postgres(pg_session):
    repo = ChanakyaRunRepository(pg_session)
    run_a = repo.create_run(owner_id="tenant-a", period="2026-11")
    run_b = repo.create_run(owner_id="tenant-b", period="2026-11")

    assert repo.get(run_a.id, owner_id="tenant-a") is not None
    assert repo.get(run_a.id, owner_id="tenant-b") is None
    assert repo.get(run_b.id, owner_id="tenant-a") is None
    assert [r.id for r in repo.list_for_owner("tenant-a")] == [run_a.id]


def test_rollback_discards_uncommitted_run(pg_session):
    repo = ChanakyaRunRepository(pg_session)
    repo.create_run(owner_id="tenant-c", period="2026-11")
    pg_session.add(MonthlyRun(owner_id="tenant-c", period="2026-12", config={}))
    pg_session.flush()
    pg_session.rollback()
    assert repo.count_recent_runs_for_owner("tenant-c", since=__import__("datetime").datetime(2020, 1, 1)) == 1


def test_cascade_delete_removes_agent_executions(pg_session):
    repo = ChanakyaRunRepository(pg_session)
    run = repo.create_run(owner_id="tenant-d", period="2026-11")
    run_id = run.id
    assert pg_session.query(AgentExecution).filter_by(run_id=run_id).count() == 7

    pg_session.delete(run)
    pg_session.commit()
    assert pg_session.query(AgentExecution).filter_by(run_id=run_id).count() == 0


def test_concurrent_sessions_see_committed_writes():
    engine = make_engine(PG_URL)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    errors: list[Exception] = []

    def create_run(owner_id: str) -> None:
        session = Session()
        try:
            ChanakyaRunRepository(session).create_run(owner_id=owner_id, period="2026-11")
        except Exception as exc:  # pragma: no cover - surfaced via errors list
            errors.append(exc)
        finally:
            session.close()

    threads = [threading.Thread(target=create_run, args=(f"concurrent-{i}",)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    verify_session = Session()
    count = (
        verify_session.query(MonthlyRun)
        .filter(MonthlyRun.owner_id.like("concurrent-%"))
        .count()
    )
    verify_session.close()
    assert count == 5

    Base.metadata.drop_all(engine)
    engine.dispose()
