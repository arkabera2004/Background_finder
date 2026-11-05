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
        linkedin_resolver,
        people_finder,
        profile_researcher,
        qa_sync,
    )

    for module in (catalogue, company_scout, people_finder, linkedin_resolver, profile_researcher, qa_sync):
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


def _run_through_profile_researcher(monkeypatch, headers) -> dict:
    from app.api.routers.chanakya import company_scout as company_scout_router
    from app.api.routers.chanakya import linkedin_resolver as resolver_router
    from app.api.routers.chanakya import people_finder as people_finder_router

    monkeypatch.setattr("app.services.company_discovery._is_safe_host", lambda hostname: True)
    monkeypatch.setattr(company_scout_router, "build_search_provider", lambda *a, **k: _FakeScoutProvider())

    run = client.post("/chanakya/runs", json={"period": "2026-11"}, headers=headers).json()
    client.post(
        f"/chanakya/runs/{run['id']}/offerings",
        json={"offerings": [{"name": "GenAI Accelerator", "icp_criteria": ["fintech"]}]},
        headers=headers,
    )
    client.post(f"/chanakya/runs/{run['id']}/company-scout", headers=headers)

    monkeypatch.setattr(people_finder_router, "build_search_provider", lambda *a, **k: _FakePeopleProvider())
    client.post(f"/chanakya/runs/{run['id']}/people-finder", headers=headers)

    monkeypatch.setattr(resolver_router, "build_search_provider", lambda *a, **k: _OneCandidateSearch())
    client.post(f"/chanakya/runs/{run['id']}/linkedin-resolver", headers=headers)

    client.post(f"/chanakya/runs/{run['id']}/profile-researcher", headers=headers)
    return run


def test_qa_sync_requires_research_briefs_first():
    run = client.post("/chanakya/runs", json={"period": "2026-11"}, headers=_auth_header()).json()

    response = client.post(f"/chanakya/runs/{run['id']}/qa-sync", headers=_auth_header())

    assert response.status_code == 409


def test_qa_sync_scores_drafts_and_requires_approval_before_export(monkeypatch):
    headers = _auth_header()
    run = _run_through_profile_researcher(monkeypatch, headers)

    response = client.post(f"/chanakya/runs/{run['id']}/qa-sync", headers=headers)

    assert response.status_code == 200
    assert response.json()["people_processed"] == 1

    run_detail = client.get(f"/chanakya/runs/{run['id']}", headers=headers).json()
    qa = next(e for e in run_detail["agent_executions"] if e["agent_name"] == "qa_sync")
    assert qa["status"] == "completed"

    records = client.get(f"/chanakya/runs/{run['id']}/qa", headers=headers).json()
    assert len(records) == 1
    assert records[0]["approval_status"] == "pending_review"
    assert records[0]["draft_subject"]

    person_id = records[0]["person_id"]
    approve_response = client.post(
        f"/chanakya/runs/{run['id']}/qa/{person_id}/approve", json={"approve": True}, headers=headers
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["approval_status"] == "approved"

    export_json = client.get(f"/chanakya/runs/{run['id']}/export", headers=headers).json()
    assert export_json["rows"][0]["approval_status"] == "approved"
    assert export_json["rows"][0]["person_name"] == "Jane Doe"

    export_csv = client.get(f"/chanakya/runs/{run['id']}/export?format=csv", headers=headers)
    assert export_csv.status_code == 200
    assert export_csv.headers["content-type"].startswith("text/csv")
    assert "Jane Doe" in export_csv.text


def test_approve_404_for_unknown_person():
    run = client.post("/chanakya/runs", json={"period": "2026-11"}, headers=_auth_header()).json()

    response = client.post(
        f"/chanakya/runs/{run['id']}/qa/nonexistent/approve", json={"approve": True}, headers=_auth_header()
    )

    assert response.status_code == 404
