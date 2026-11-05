"""Phase 12: a single deterministic fixture test driving the entire
Chanakya monthly pipeline — run creation through QA approval and export
— in one place, as the "full end-to-end monthly pipeline" the master
prompt's testing section asks for. The individual per-agent test files
already cover each agent's edge cases; this one proves the whole chain
actually composes, start to finish, with nothing silently dropped
between stages.
"""

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


def _auth_header(user_id: str = "ceo-user") -> dict:
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


def test_full_monthly_pipeline_from_run_creation_to_approved_export(monkeypatch):
    from app.api.routers.chanakya import company_scout as company_scout_router
    from app.api.routers.chanakya import linkedin_resolver as resolver_router
    from app.api.routers.chanakya import people_finder as people_finder_router

    monkeypatch.setattr("app.services.company_discovery._is_safe_host", lambda hostname: True)
    monkeypatch.setattr(company_scout_router, "build_search_provider", lambda *a, **k: _FakeScoutProvider())
    monkeypatch.setattr(people_finder_router, "build_search_provider", lambda *a, **k: _FakePeopleProvider())
    monkeypatch.setattr(resolver_router, "build_search_provider", lambda *a, **k: _OneCandidateSearch())

    headers = _auth_header()

    # Step 1: Agent 01 — create the monthly run and submit the offering/ICP brief.
    run = client.post("/chanakya/runs", json={"period": "2026-11"}, headers=headers).json()
    assert run["status"] == "pending"
    assert len(run["agent_executions"]) == 7

    offering_response = client.post(
        f"/chanakya/runs/{run['id']}/offerings",
        json={
            "offerings": [
                {"name": "GenAI Accelerator", "icp_criteria": ["fintech", "Series B"]},
            ],
            "filters": {"industries": ["fintech"]},
        },
        headers=headers,
    )
    assert offering_response.status_code == 201
    assert offering_response.json()["version"] == 1

    # Step 2: Agents 02-07 — orchestrated in one call.
    orchestrate_response = client.post(f"/chanakya/runs/{run['id']}/orchestrate", headers=headers)
    assert orchestrate_response.status_code == 200
    body = orchestrate_response.json()
    assert body["stopped_at"] is None
    assert len(body["stages"]) == 6
    assert all(s["status"] == "completed" for s in body["stages"])

    # Step 3: verify every agent actually produced something real, not empty shells.
    companies = client.get(f"/chanakya/runs/{run['id']}/companies", headers=headers).json()
    assert len(companies) == 1
    assert companies[0]["domain"] == "acme.com"
    assert companies[0]["selected"] is True

    people = client.get(f"/chanakya/runs/{run['id']}/people", headers=headers).json()
    assert len(people) == 1
    assert people[0]["identity_confirmed"] is True
    assert people[0]["linkedin_url"] == "https://linkedin.com/in/janedoe"

    emails = client.get(f"/chanakya/runs/{run['id']}/emails", headers=headers).json()
    assert len(emails) == 5  # 5 patterns for the one confirmed person
    assert any(e["email"].startswith("jane") for e in emails)

    briefs = client.get(f"/chanakya/runs/{run['id']}/briefs", headers=headers).json()
    assert len(briefs) == 1

    qa_records = client.get(f"/chanakya/runs/{run['id']}/qa", headers=headers).json()
    assert len(qa_records) == 1
    assert qa_records[0]["approval_status"] == "pending_review"

    # Step 4: human approval gate — nothing is sendable until this happens.
    person_id = qa_records[0]["person_id"]
    approve_response = client.post(
        f"/chanakya/runs/{run['id']}/qa/{person_id}/approve", json={"approve": True}, headers=headers
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["approval_status"] == "approved"

    # Step 5: export reflects the approved state.
    export = client.get(f"/chanakya/runs/{run['id']}/export", headers=headers).json()
    assert export["rows"][0]["approval_status"] == "approved"
    assert export["rows"][0]["company_name"] == "Acme fintech"
    assert export["rows"][0]["person_name"] == "Jane Doe"

    # Step 6: re-running the full chain is a safe no-op (idempotent/resumable).
    rerun = client.post(f"/chanakya/runs/{run['id']}/orchestrate", headers=headers).json()
    assert all(s["status"] == "skipped_already_completed" for s in rerun["stages"])
    assert len(client.get(f"/chanakya/runs/{run['id']}/companies", headers=headers).json()) == 1
    assert len(client.get(f"/chanakya/runs/{run['id']}/people", headers=headers).json()) == 1
    # the approval decision survived the rerun (qa-sync is skipped, not re-scored)
    qa_after_rerun = client.get(f"/chanakya/runs/{run['id']}/qa", headers=headers).json()
    assert qa_after_rerun[0]["approval_status"] == "approved"
