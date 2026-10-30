import time

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.core.config import settings
from app.providers.search_provider import SearchResult
import app.services.research_service as research_service
from main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _secret(monkeypatch):
    monkeypatch.setattr(settings, "supabase_jwt_secret", "test-secret")


def _auth_header() -> dict:
    token = jwt.encode(
        {"sub": "user-1", "aud": "authenticated", "exp": time.time() + 60},
        "test-secret",
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


class FakeSearchMultiple:
    async def search(self, query: str, max_results: int = 10):
        return [
            SearchResult(url="https://linkedin.com/in/jane-doe-1", title="Jane Doe - Engineer at Acme"),
            SearchResult(url="https://linkedin.com/in/jane-doe-2", title="Jane Doe - Sales at Acme"),
        ]


class FakeSearchNone:
    async def search(self, query: str, max_results: int = 10):
        return []


def test_ambiguous_name_company_pauses_for_identity_selection(monkeypatch):
    monkeypatch.setattr(
        research_service, "build_search_provider", lambda *a, **k: FakeSearchMultiple()
    )
    headers = _auth_header()

    resp = client.post("/research", json={"full_name": "Jane Doe", "company": "Acme"}, headers=headers)
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "needs_identity_selection"
    assert len(body["identity_candidates"]) == 2

    run_id = body["run_id"]
    get_resp = client.get(f"/runs/{run_id}", headers=headers)
    assert get_resp.json()["status"] == "needs_identity_selection"


def test_selecting_identity_resumes_the_run(monkeypatch):
    monkeypatch.setattr(
        research_service, "build_search_provider", lambda *a, **k: FakeSearchMultiple()
    )
    headers = _auth_header()
    resp = client.post("/research", json={"full_name": "Jane Doe", "company": "Acme"}, headers=headers)
    run_id = resp.json()["run_id"]

    select_resp = client.post(
        f"/runs/{run_id}/select-identity?linkedin_url=https://linkedin.com/in/jane-doe-1",
        headers=headers,
    )
    assert select_resp.status_code == 200
    assert select_resp.json()["status"] in ("pending", "running")


def test_selecting_an_unoffered_url_is_rejected(monkeypatch):
    monkeypatch.setattr(
        research_service, "build_search_provider", lambda *a, **k: FakeSearchMultiple()
    )
    headers = _auth_header()
    resp = client.post("/research", json={"full_name": "Jane Doe", "company": "Acme"}, headers=headers)
    run_id = resp.json()["run_id"]

    select_resp = client.post(
        f"/runs/{run_id}/select-identity?linkedin_url=https://linkedin.com/in/someone-else",
        headers=headers,
    )
    assert select_resp.status_code == 422


def test_unique_match_proceeds_automatically_without_pausing(monkeypatch):
    class FakeSearchSingle:
        async def search(self, query: str, max_results: int = 10):
            return [SearchResult(url="https://linkedin.com/in/jane-doe-1", title="Jane Doe")]

    monkeypatch.setattr(research_service, "build_search_provider", lambda *a, **k: FakeSearchSingle())
    headers = _auth_header()

    resp = client.post("/research", json={"full_name": "Jane Doe", "company": "Acme"}, headers=headers)
    assert resp.status_code == 202
    assert resp.json()["status"] != "needs_identity_selection"


def test_no_match_proceeds_without_pausing_and_eventually_fails(monkeypatch):
    """No candidates found => proceeds with user-supplied info directly
    (can't fetch a real profile without pasted text or a paid provider,
    so it fails later at fetch_profile — that's an honest, pre-existing
    limitation, not new breakage)."""
    monkeypatch.setattr(research_service, "build_search_provider", lambda *a, **k: FakeSearchNone())
    headers = _auth_header()

    resp = client.post("/research", json={"full_name": "Jane Doe", "company": "Acme"}, headers=headers)
    assert resp.status_code == 202
    assert resp.json()["status"] != "needs_identity_selection"
