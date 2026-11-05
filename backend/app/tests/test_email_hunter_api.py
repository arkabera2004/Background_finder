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

    from app.api.routers.chanakya import catalogue, company_scout, email_hunter, linkedin_resolver, people_finder

    for module in (catalogue, company_scout, people_finder, linkedin_resolver, email_hunter):
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


def _run_through_resolver(monkeypatch, headers) -> dict:
    from app.api.routers.chanakya import company_scout as company_scout_router
    from app.api.routers.chanakya import linkedin_resolver as resolver_router
    from app.api.routers.chanakya import people_finder as people_finder_router

    monkeypatch.setattr("app.services.company_discovery._is_safe_host", lambda hostname: True)
    monkeypatch.setattr(company_scout_router, "build_search_provider", lambda *a, **k: _FakeScoutProvider())

    run = client.post("/chanakya/runs", json={"period": "2026-11"}, headers=headers).json()
    client.post(
        f"/chanakya/runs/{run['id']}/offerings",
        json={"offerings": [{"name": "X", "icp_criteria": ["fintech"]}]},
        headers=headers,
    )
    client.post(f"/chanakya/runs/{run['id']}/company-scout", headers=headers)

    monkeypatch.setattr(people_finder_router, "build_search_provider", lambda *a, **k: _FakePeopleProvider())
    client.post(f"/chanakya/runs/{run['id']}/people-finder", headers=headers)

    monkeypatch.setattr(resolver_router, "build_search_provider", lambda *a, **k: _OneCandidateSearch())
    client.post(f"/chanakya/runs/{run['id']}/linkedin-resolver", headers=headers)
    return run


def test_email_hunter_requires_confirmed_people_first():
    run = client.post("/chanakya/runs", json={"period": "2026-11"}, headers=_auth_header()).json()

    response = client.post(f"/chanakya/runs/{run['id']}/email-hunter", headers=_auth_header())

    assert response.status_code == 409


def test_email_hunter_generates_and_persists_candidates_for_confirmed_people(monkeypatch):
    headers = _auth_header()
    run = _run_through_resolver(monkeypatch, headers)

    response = client.post(f"/chanakya/runs/{run['id']}/email-hunter", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["people_processed"] == 1

    run_detail = client.get(f"/chanakya/runs/{run['id']}", headers=headers).json()
    hunter = next(e for e in run_detail["agent_executions"] if e["agent_name"] == "email_hunter")
    assert hunter["status"] == "completed"

    emails = client.get(f"/chanakya/runs/{run['id']}/emails", headers=headers).json()
    assert len(emails) == 5  # 5 patterns x 1 confirmed person
    assert all(e["verification_status"] == "needs_review" for e in emails)  # no verifier configured
    assert "jane.doe@acme.com" in {e["email"] for e in emails}


def test_email_hunter_emails_endpoint_filters_by_person(monkeypatch):
    headers = _auth_header()
    run = _run_through_resolver(monkeypatch, headers)
    client.post(f"/chanakya/runs/{run['id']}/email-hunter", headers=headers)

    person_id = client.get(f"/chanakya/runs/{run['id']}/people", headers=headers).json()[0]["id"]

    response = client.get(f"/chanakya/runs/{run['id']}/emails?person_id={person_id}", headers=headers)

    assert response.status_code == 200
    assert len(response.json()) == 5
    assert all(e["person_id"] == person_id for e in response.json())
