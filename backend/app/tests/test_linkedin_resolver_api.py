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

    from app.api.routers.chanakya import catalogue, company_scout, linkedin_resolver, people_finder

    for module in (catalogue, company_scout, people_finder, linkedin_resolver):
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


def _run_through_people_finder(monkeypatch, headers) -> dict:
    from app.api.routers.chanakya import company_scout as company_scout_router
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
    return run


def test_linkedin_resolver_requires_people_finder_first():
    run = client.post("/chanakya/runs", json={"period": "2026-11"}, headers=_auth_header()).json()

    response = client.post(f"/chanakya/runs/{run['id']}/linkedin-resolver", headers=_auth_header())

    assert response.status_code == 409


class _OneCandidateSearch(SearchProvider):
    name = "one"

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        return [SearchResult(url="https://linkedin.com/in/janedoe", title="Jane Doe - Acme fintech")]


class _TwoCandidateSearch(SearchProvider):
    name = "two"

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        return [
            SearchResult(url="https://linkedin.com/in/janedoe", title="Jane Doe A - Acme fintech"),
            SearchResult(url="https://linkedin.com/in/janedoe2", title="Jane Doe B - Acme fintech"),
        ]


def test_linkedin_resolver_confirms_single_match(monkeypatch):
    from app.api.routers.chanakya import linkedin_resolver as resolver_router

    headers = _auth_header()
    run = _run_through_people_finder(monkeypatch, headers)

    monkeypatch.setattr(resolver_router, "build_search_provider", lambda *a, **k: _OneCandidateSearch())
    response = client.post(f"/chanakya/runs/{run['id']}/linkedin-resolver", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["confirmed"] == 1
    assert body["ambiguous"] == 0
    assert body["unresolved"] == 0

    people = client.get(f"/chanakya/runs/{run['id']}/people", headers=headers).json()
    assert all(p["identity_confirmed"] is True for p in people)
    assert all(p["linkedin_url"] == "https://linkedin.com/in/janedoe" for p in people)

    assert client.get(f"/chanakya/runs/{run['id']}/people/needs-review", headers=headers).json() == []


def test_linkedin_resolver_queues_ambiguous_for_manual_review_then_manual_confirm(monkeypatch):
    from app.api.routers.chanakya import linkedin_resolver as resolver_router

    headers = _auth_header()
    run = _run_through_people_finder(monkeypatch, headers)

    monkeypatch.setattr(resolver_router, "build_search_provider", lambda *a, **k: _TwoCandidateSearch())
    response = client.post(f"/chanakya/runs/{run['id']}/linkedin-resolver", headers=headers)

    assert response.json()["ambiguous"] == 1

    needs_review = client.get(f"/chanakya/runs/{run['id']}/people/needs-review", headers=headers).json()
    assert len(needs_review) == 1
    assert needs_review[0]["identity_confirmed"] is False
    assert len(needs_review[0]["candidate_profiles"]) == 2

    person_id = needs_review[0]["id"]
    resolve_response = client.post(
        f"/chanakya/runs/{run['id']}/people/{person_id}/resolve",
        json={"linkedin_url": "https://linkedin.com/in/janedoe2"},
        headers=headers,
    )

    assert resolve_response.status_code == 200
    assert resolve_response.json()["identity_confirmed"] is True
    assert resolve_response.json()["linkedin_url"] == "https://linkedin.com/in/janedoe2"
    assert client.get(f"/chanakya/runs/{run['id']}/people/needs-review", headers=headers).json() == []


def test_manual_resolve_rejects_non_linkedin_url(monkeypatch):
    headers = _auth_header()
    run = _run_through_people_finder(monkeypatch, headers)
    person_id = client.get(f"/chanakya/runs/{run['id']}/people", headers=headers).json()[0]["id"]

    response = client.post(
        f"/chanakya/runs/{run['id']}/people/{person_id}/resolve",
        json={"linkedin_url": "https://example.com/janedoe"},
        headers=headers,
    )

    assert response.status_code == 422


def test_manual_resolve_404_for_unknown_person(monkeypatch):
    headers = _auth_header()
    run = _run_through_people_finder(monkeypatch, headers)

    response = client.post(
        f"/chanakya/runs/{run['id']}/people/nonexistent/resolve",
        json={"linkedin_url": "https://linkedin.com/in/janedoe"},
        headers=headers,
    )

    assert response.status_code == 404
