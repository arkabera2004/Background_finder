"""Phase 5 — durable monthly scheduler: CRUD API + the daily ARQ cron
function that drives due schedules end-to-end, unattended.
"""

import time

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.chanakya_repository import ChanakyaRunRepository
from app.db.session import init_db, make_engine
from app.providers.search_provider import SearchProvider, SearchResult
from main import app

client = TestClient(app)

_test_session_factory = None


@pytest.fixture(autouse=True)
def _isolated_db(monkeypatch):
    global _test_session_factory

    engine = make_engine("sqlite:///:memory:")
    init_db(bind=engine)
    _test_session_factory = sessionmaker(bind=engine)

    from app.api.routers.chanakya import (
        catalogue,
        company_scout,
        email_hunter,
        linkedin_resolver,
        orchestrator,
        people_finder,
        profile_researcher,
        qa_sync,
        schedules,
    )
    from app.workers import main as worker_main

    for module in (
        catalogue,
        company_scout,
        people_finder,
        linkedin_resolver,
        email_hunter,
        profile_researcher,
        qa_sync,
        orchestrator,
        schedules,
        worker_main,
    ):
        monkeypatch.setattr(module, "get_session", lambda: _test_session_factory())
    monkeypatch.setattr(settings, "supabase_jwt_secret", "test-secret")


def _auth_header(user_id: str = "tenant-1") -> dict:
    token = jwt.encode(
        {"sub": user_id, "aud": "authenticated", "exp": time.time() + 60},
        "test-secret",
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


class _FakeScoutProvider(SearchProvider):
    name = "fake-scout"

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        return [SearchResult(url="https://acme.com/about", title="Acme fintech", snippet="fintech Series B")]


class _FakePeopleProvider(SearchProvider):
    name = "fake-people"

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        return [SearchResult(url="https://linkedin.com/in/janedoe", title="Jane Doe - CEO - Acme | LinkedIn")]


class _OneCandidateSearch(SearchProvider):
    name = "one"

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        return [SearchResult(url="https://linkedin.com/in/janedoe", title="Jane Doe - Acme fintech")]


def _schedule_payload(day_of_month: int = 1) -> dict:
    return {
        "offerings": [{"name": "GenAI Accelerator", "icp_criteria": ["fintech", "Series B"]}],
        "filters": {"industries": ["fintech"]},
        "day_of_month": day_of_month,
    }


def test_create_list_update_delete_schedule():
    headers = _auth_header()
    created = client.post("/chanakya/schedules", json=_schedule_payload(), headers=headers)
    assert created.status_code == 201
    schedule_id = created.json()["id"]
    assert created.json()["enabled"] is True

    listed = client.get("/chanakya/schedules", headers=headers).json()
    assert len(listed) == 1

    disabled = client.patch(
        f"/chanakya/schedules/{schedule_id}", json={"enabled": False}, headers=headers
    )
    assert disabled.json()["enabled"] is False

    other_owner = client.get("/chanakya/schedules", headers=_auth_header("tenant-2")).json()
    assert other_owner == []

    delete_response = client.delete(f"/chanakya/schedules/{schedule_id}", headers=headers)
    assert delete_response.status_code == 204
    assert client.get("/chanakya/schedules", headers=headers).json() == []


def test_schedule_rejects_empty_offerings_and_bad_day():
    headers = _auth_header()
    bad_offerings = client.post(
        "/chanakya/schedules", json={"offerings": [], "day_of_month": 1}, headers=headers
    )
    assert bad_offerings.status_code == 422

    bad_day = client.post("/chanakya/schedules", json=_schedule_payload(day_of_month=31), headers=headers)
    assert bad_day.status_code == 422


@pytest.mark.asyncio
async def test_due_schedule_drives_a_full_run_unattended(monkeypatch):
    from app.api.routers.chanakya import company_scout as company_scout_router
    from app.api.routers.chanakya import linkedin_resolver as resolver_router
    from app.api.routers.chanakya import people_finder as people_finder_router
    from app.workers.main import run_due_chanakya_schedules

    monkeypatch.setattr("app.services.company_discovery._is_safe_host", lambda hostname: True)
    monkeypatch.setattr(company_scout_router, "build_search_provider", lambda *a, **k: _FakeScoutProvider())
    monkeypatch.setattr(people_finder_router, "build_search_provider", lambda *a, **k: _FakePeopleProvider())
    monkeypatch.setattr(resolver_router, "build_search_provider", lambda *a, **k: _OneCandidateSearch())

    headers = _auth_header("tenant-auto")
    client.post("/chanakya/schedules", json=_schedule_payload(day_of_month=1), headers=headers)

    outcome = await run_due_chanakya_schedules(ctx={})
    assert len(outcome["results"]) == 1
    assert outcome["results"][0]["status"] == "ok"

    session = _test_session_factory()
    repo = ChanakyaRunRepository(session)
    runs = repo.list_for_owner("tenant-auto")
    assert len(runs) == 1
    assert runs[0].period == outcome["period"]
    companies = client.get(f"/chanakya/runs/{runs[0].id}/companies", headers=headers).json()
    assert len(companies) == 1
    session.close()

    # A second tick in the same period is a no-op — no duplicate run created.
    outcome_2 = await run_due_chanakya_schedules(ctx={})
    assert outcome_2["results"] == []
    session = _test_session_factory()
    assert len(ChanakyaRunRepository(session).list_for_owner("tenant-auto")) == 1
    session.close()


@pytest.mark.asyncio
async def test_schedule_failure_is_isolated_from_other_tenants(monkeypatch):
    from app.workers.main import run_due_chanakya_schedules

    # Force the first step of the scheduled run to blow up, proving one
    # tenant's failure is recorded and does not raise out of the cron.
    async def _boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("app.workers.main.submit_run", _boom)

    headers = _auth_header("tenant-broken")
    client.post("/chanakya/schedules", json=_schedule_payload(), headers=headers)

    outcome = await run_due_chanakya_schedules(ctx={})
    assert outcome["results"][0]["status"] == "failed"
    assert "boom" in outcome["results"][0]["error"]
