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

    import app.api.routers.chanakya as chanakya_router

    monkeypatch.setattr(chanakya_router, "get_session", lambda: _test_session_factory())
    monkeypatch.setattr(settings, "supabase_jwt_secret", "test-secret")


def _auth_header(user_id: str = "test-user") -> dict:
    token = jwt.encode(
        {"sub": user_id, "aud": "authenticated", "exp": time.time() + 60},
        "test-secret",
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def test_create_run_seeds_pending_agent_executions():
    response = client.post("/chanakya/runs", json={"period": "2026-11"}, headers=_auth_header())

    assert response.status_code == 201
    body = response.json()
    assert body["period"] == "2026-11"
    assert body["status"] == "pending"
    assert len(body["agent_executions"]) == 7
    assert all(e["status"] == "pending" for e in body["agent_executions"])


def test_create_run_rejects_bad_period():
    response = client.post("/chanakya/runs", json={"period": "november"}, headers=_auth_header())

    assert response.status_code == 422


def test_list_runs_is_owner_scoped():
    client.post("/chanakya/runs", json={"period": "2026-11"}, headers=_auth_header("owner-a"))
    client.post("/chanakya/runs", json={"period": "2026-11"}, headers=_auth_header("owner-b"))

    response = client.get("/chanakya/runs", headers=_auth_header("owner-a"))

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_run_cross_owner_returns_404():
    run = client.post("/chanakya/runs", json={"period": "2026-11"}, headers=_auth_header("owner-a")).json()

    response = client.get(f"/chanakya/runs/{run['id']}", headers=_auth_header("owner-b"))

    assert response.status_code == 404


def test_submit_offering_brief_completes_catalogue_agent():
    run = client.post("/chanakya/runs", json={"period": "2026-11"}, headers=_auth_header()).json()

    response = client.post(
        f"/chanakya/runs/{run['id']}/offerings",
        json={
            "offerings": [
                {"name": "GenAI Accelerator", "description": "...", "icp_criteria": ["Series B+", "100-1000 employees"]}
            ],
            "filters": {"industries": ["fintech"]},
        },
        headers=_auth_header(),
    )

    assert response.status_code == 201
    assert response.json()["version"] == 1

    run_detail = client.get(f"/chanakya/runs/{run['id']}", headers=_auth_header()).json()
    catalogue = next(e for e in run_detail["agent_executions"] if e["agent_name"] == "catalogue")
    assert catalogue["status"] == "completed"
    assert catalogue["output_summary"] == {"offering_count": 1, "version": 1}


def test_submit_offering_brief_rejects_empty_offerings():
    run = client.post("/chanakya/runs", json={"period": "2026-11"}, headers=_auth_header()).json()

    response = client.post(
        f"/chanakya/runs/{run['id']}/offerings", json={"offerings": []}, headers=_auth_header()
    )

    assert response.status_code == 422


def test_resubmitting_offering_brief_creates_new_version_not_overwrite():
    run = client.post("/chanakya/runs", json={"period": "2026-11"}, headers=_auth_header()).json()
    headers = _auth_header()

    client.post(
        f"/chanakya/runs/{run['id']}/offerings",
        json={"offerings": [{"name": "Accelerator A"}]},
        headers=headers,
    )
    client.post(
        f"/chanakya/runs/{run['id']}/offerings",
        json={"offerings": [{"name": "Accelerator A"}, {"name": "Accelerator B"}]},
        headers=headers,
    )

    response = client.get(f"/chanakya/runs/{run['id']}/offerings", headers=headers)

    assert response.status_code == 200
    versions = response.json()
    assert len(versions) == 2
    assert versions[0]["version"] == 1
    assert len(versions[0]["data"]["offerings"]) == 1
    assert versions[1]["version"] == 2
    assert len(versions[1]["data"]["offerings"]) == 2


class _FakeSearchProvider(SearchProvider):
    name = "fake"

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        return [
            SearchResult(url="https://acme.com/about", title="Acme fintech", snippet="Series B fintech company"),
            SearchResult(url="https://globex.com/about", title="Globex fintech", snippet="Series B fintech"),
        ]


def test_company_scout_requires_offering_brief_first():
    run = client.post("/chanakya/runs", json={"period": "2026-11"}, headers=_auth_header()).json()

    response = client.post(f"/chanakya/runs/{run['id']}/company-scout", headers=_auth_header())

    assert response.status_code == 409


def test_company_scout_discovers_scores_and_selects(monkeypatch):
    import app.api.routers.chanakya as chanakya_router

    monkeypatch.setattr(chanakya_router, "build_search_provider", lambda *a, **k: _FakeSearchProvider())
    monkeypatch.setattr(
        "app.services.company_discovery._is_safe_host", lambda hostname: True
    )

    headers = _auth_header()
    run = client.post("/chanakya/runs", json={"period": "2026-11"}, headers=headers).json()
    client.post(
        f"/chanakya/runs/{run['id']}/offerings",
        json={
            "offerings": [{"name": "GenAI Accelerator", "icp_criteria": ["fintech", "Series B"]}],
            "filters": {"industries": []},
        },
        headers=headers,
    )

    response = client.post(f"/chanakya/runs/{run['id']}/company-scout", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["candidates_found"] == 2
    assert len(body["selected"]) == 2
    assert {c["domain"] for c in body["selected"]} == {"acme.com", "globex.com"}

    run_detail = client.get(f"/chanakya/runs/{run['id']}", headers=headers).json()
    scout = next(e for e in run_detail["agent_executions"] if e["agent_name"] == "company_scout")
    assert scout["status"] == "completed"

    companies = client.get(f"/chanakya/runs/{run['id']}/companies", headers=headers).json()
    assert len(companies) == 2


def test_company_scout_respects_configured_target_count(monkeypatch):
    import app.api.routers.chanakya as chanakya_router

    monkeypatch.setattr(chanakya_router, "build_search_provider", lambda *a, **k: _FakeSearchProvider())
    monkeypatch.setattr("app.services.company_discovery._is_safe_host", lambda hostname: True)

    headers = _auth_header()
    run = client.post(
        "/chanakya/runs", json={"period": "2026-11", "config": {"target_company_count": 1}}, headers=headers
    ).json()
    client.post(
        f"/chanakya/runs/{run['id']}/offerings",
        json={"offerings": [{"name": "X", "icp_criteria": ["fintech"]}]},
        headers=headers,
    )

    response = client.post(f"/chanakya/runs/{run['id']}/company-scout", headers=headers)

    assert len(response.json()["selected"]) == 1
    assert len(client.get(f"/chanakya/runs/{run['id']}/companies", headers=headers).json()) == 2
    assert (
        len(
            client.get(
                f"/chanakya/runs/{run['id']}/companies?selected_only=true", headers=headers
            ).json()
        )
        == 1
    )


def test_offerings_endpoints_404_for_unknown_run():
    headers = _auth_header()
    assert client.get("/chanakya/runs/nonexistent/offerings", headers=headers).status_code == 404
    assert (
        client.post(
            "/chanakya/runs/nonexistent/offerings",
            json={"offerings": [{"name": "X"}]},
            headers=headers,
        ).status_code
        == 404
    )
