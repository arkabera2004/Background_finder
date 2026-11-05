import time

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.session import init_db, make_engine
from app.providers.search_provider import SearchProvider, SearchResult
from main import app

client = TestClient(app)

_test_engine = None
_test_session_factory = None


@pytest.fixture(autouse=True)
def _isolated_db(monkeypatch):
    global _test_engine, _test_session_factory

    _test_engine = make_engine("sqlite:///:memory:")
    init_db(bind=_test_engine)
    _test_session_factory = sessionmaker(bind=_test_engine)

    from app.api.routers.chanakya import (
        catalogue,
        company_scout,
        email_hunter,
        linkedin_resolver,
        orchestrator,
        people_finder,
        profile_researcher,
        qa_sync,
    )

    for module in (
        catalogue,
        company_scout,
        people_finder,
        linkedin_resolver,
        email_hunter,
        profile_researcher,
        qa_sync,
        orchestrator,
    ):
        monkeypatch.setattr(module, "get_session", lambda: _test_session_factory())
    monkeypatch.setattr(settings, "supabase_jwt_secret", "test-secret")


def _auth_header(user_id: str = "test-user") -> dict:
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
        return [SearchResult(url="https://linkedin.com/in/janedoe", title="Jane Doe")]


def test_orchestrate_404_for_unknown_run():
    response = client.post("/chanakya/runs/nonexistent/orchestrate", headers=_auth_header())

    assert response.status_code == 404


def test_orchestrate_stops_at_company_scout_without_an_offering_brief():
    headers = _auth_header()
    run = client.post("/chanakya/runs", json={"period": "2026-11"}, headers=headers).json()

    response = client.post(f"/chanakya/runs/{run['id']}/orchestrate", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["stopped_at"] == "company_scout"
    assert body["stages"][0]["status"] == "stopped"


def test_orchestrate_runs_all_six_stages_end_to_end(monkeypatch):
    from app.api.routers.chanakya import company_scout as company_scout_router
    from app.api.routers.chanakya import linkedin_resolver as resolver_router
    from app.api.routers.chanakya import people_finder as people_finder_router

    monkeypatch.setattr("app.services.company_discovery._is_safe_host", lambda hostname: True)
    monkeypatch.setattr(company_scout_router, "build_search_provider", lambda *a, **k: _FakeScoutProvider())
    monkeypatch.setattr(people_finder_router, "build_search_provider", lambda *a, **k: _FakePeopleProvider())
    monkeypatch.setattr(resolver_router, "build_search_provider", lambda *a, **k: _OneCandidateSearch())

    headers = _auth_header()
    run = client.post("/chanakya/runs", json={"period": "2026-11"}, headers=headers).json()
    client.post(
        f"/chanakya/runs/{run['id']}/offerings",
        json={"offerings": [{"name": "GenAI Accelerator", "icp_criteria": ["fintech"]}]},
        headers=headers,
    )

    response = client.post(f"/chanakya/runs/{run['id']}/orchestrate", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["stopped_at"] is None
    assert [s["agent"] for s in body["stages"]] == [
        "company_scout",
        "people_finder",
        "linkedin_resolver",
        "email_hunter",
        "profile_researcher",
        "qa_sync",
    ]
    assert all(s["status"] == "completed" for s in body["stages"])

    run_detail = client.get(f"/chanakya/runs/{run['id']}", headers=headers).json()
    assert run_detail["agent_executions"][-1]["status"] == "completed"


def test_orchestrate_is_idempotent_on_rerun(monkeypatch):
    from app.api.routers.chanakya import company_scout as company_scout_router
    from app.api.routers.chanakya import linkedin_resolver as resolver_router
    from app.api.routers.chanakya import people_finder as people_finder_router

    monkeypatch.setattr("app.services.company_discovery._is_safe_host", lambda hostname: True)
    monkeypatch.setattr(company_scout_router, "build_search_provider", lambda *a, **k: _FakeScoutProvider())
    monkeypatch.setattr(people_finder_router, "build_search_provider", lambda *a, **k: _FakePeopleProvider())
    monkeypatch.setattr(resolver_router, "build_search_provider", lambda *a, **k: _OneCandidateSearch())

    headers = _auth_header()
    run = client.post("/chanakya/runs", json={"period": "2026-11"}, headers=headers).json()
    client.post(
        f"/chanakya/runs/{run['id']}/offerings",
        json={"offerings": [{"name": "GenAI Accelerator", "icp_criteria": ["fintech"]}]},
        headers=headers,
    )
    client.post(f"/chanakya/runs/{run['id']}/orchestrate", headers=headers)

    response = client.post(f"/chanakya/runs/{run['id']}/orchestrate", headers=headers)

    assert response.status_code == 200
    assert all(s["status"] == "skipped_already_completed" for s in response.json()["stages"])

    # re-running didn't duplicate any companies/people/emails
    assert len(client.get(f"/chanakya/runs/{run['id']}/companies", headers=headers).json()) == 1
    assert len(client.get(f"/chanakya/runs/{run['id']}/people", headers=headers).json()) == 1
