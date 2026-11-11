"""Phase 11 security hardening: prove every Chanakya sub-resource read is
scoped to the run's owner, not just the run itself. Each endpoint calls
get_run_or_404(repo, run_id, owner_id) before touching anything else, so
these should already 404 by construction — this test file exists to make
that guarantee explicit and regression-proof rather than assumed.
"""

import time

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.session import init_db, make_engine
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


def _auth_header(user_id: str) -> dict:
    token = jwt.encode(
        {"sub": user_id, "aud": "authenticated", "exp": time.time() + 60},
        "test-secret",
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize(
    "path_suffix",
    [
        "/offerings",
        "/companies",
        "/people",
        "/people/needs-review",
        "/emails",
        "/briefs",
        "/qa",
        "/export",
    ],
)
def test_cross_owner_get_endpoints_404(path_suffix):
    owner_header = _auth_header("owner-a")
    attacker_header = _auth_header("owner-b")
    run = client.post("/chanakya/runs", json={"period": "2026-11"}, headers=owner_header).json()

    response = client.get(f"/chanakya/runs/{run['id']}{path_suffix}", headers=attacker_header)

    assert response.status_code == 404


@pytest.mark.parametrize(
    "path_suffix,method",
    [
        ("/offerings", "post"),
        ("/company-scout", "post"),
        ("/people-finder", "post"),
        ("/linkedin-resolver", "post"),
        ("/email-hunter", "post"),
        ("/profile-researcher", "post"),
        ("/qa-sync", "post"),
        ("/orchestrate", "post"),
    ],
)
def test_cross_owner_action_endpoints_404(path_suffix, method):
    owner_header = _auth_header("owner-a")
    attacker_header = _auth_header("owner-b")
    run = client.post("/chanakya/runs", json={"period": "2026-11"}, headers=owner_header).json()

    body = {"offerings": [{"name": "X"}]} if path_suffix == "/offerings" else None
    response = client.post(
        f"/chanakya/runs/{run['id']}{path_suffix}", json=body, headers=attacker_header
    )

    assert response.status_code == 404


def test_cross_owner_cannot_resolve_or_approve_a_person():
    owner_header = _auth_header("owner-a")
    attacker_header = _auth_header("owner-b")
    run = client.post("/chanakya/runs", json={"period": "2026-11"}, headers=owner_header).json()

    resolve_response = client.post(
        f"/chanakya/runs/{run['id']}/people/anyone/resolve",
        json={"linkedin_url": "https://linkedin.com/in/someone"},
        headers=attacker_header,
    )
    approve_response = client.post(
        f"/chanakya/runs/{run['id']}/qa/anyone/approve", json={"approve": True}, headers=attacker_header
    )

    assert resolve_response.status_code == 404
    assert approve_response.status_code == 404


def test_list_runs_never_leaks_another_owners_runs():
    client.post("/chanakya/runs", json={"period": "2026-10"}, headers=_auth_header("owner-a"))
    client.post("/chanakya/runs", json={"period": "2026-11"}, headers=_auth_header("owner-a"))
    client.post("/chanakya/runs", json={"period": "2026-11"}, headers=_auth_header("owner-b"))

    owner_a_runs = client.get("/chanakya/runs", headers=_auth_header("owner-a")).json()
    owner_b_runs = client.get("/chanakya/runs", headers=_auth_header("owner-b")).json()

    assert len(owner_a_runs) == 2
    assert len(owner_b_runs) == 1


def test_list_all_companies_never_leaks_another_owners_companies(monkeypatch):
    from app.api.routers.chanakya import company_scout as company_scout_router
    from app.providers.search_provider import SearchProvider, SearchResult

    class _FakeScout(SearchProvider):
        name = "fake"

        async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
            return [SearchResult(url="https://acme.com/about", title="Acme fintech", snippet="fintech")]

    monkeypatch.setattr("app.services.company_discovery._is_safe_host", lambda hostname: True)
    monkeypatch.setattr(company_scout_router, "build_search_provider", lambda *a, **k: _FakeScout())

    headers_a = _auth_header("owner-a")
    headers_b = _auth_header("owner-b")
    run_a = client.post("/chanakya/runs", json={"period": "2026-11"}, headers=headers_a).json()
    client.post(
        f"/chanakya/runs/{run_a['id']}/offerings",
        json={"offerings": [{"name": "X", "icp_criteria": ["fintech"]}]},
        headers=headers_a,
    )
    client.post(f"/chanakya/runs/{run_a['id']}/company-scout", headers=headers_a)

    owner_a_companies = client.get("/chanakya/companies", headers=headers_a).json()
    owner_b_companies = client.get("/chanakya/companies", headers=headers_b).json()

    assert len(owner_a_companies) == 1
    assert owner_a_companies[0]["domain"] == "acme.com"
    assert owner_b_companies == []
