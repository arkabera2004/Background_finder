import time

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.session import init_db, make_engine
from main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _isolated_db(monkeypatch):
    """Each test gets its own fresh in-memory SQLite DB, not the shared
    module-level engine (which would leak state across tests)."""
    test_engine = make_engine("sqlite:///:memory:")
    init_db(bind=test_engine)
    TestSessionLocal = sessionmaker(bind=test_engine)

    import app.api.routers.prospects as prospects_router

    monkeypatch.setattr(prospects_router, "get_session", lambda: TestSessionLocal())
    monkeypatch.setattr(settings, "supabase_jwt_secret", "test-secret")


def _auth_header(user_id: str = "user-1") -> dict:
    token = jwt.encode(
        {"sub": user_id, "aud": "authenticated", "exp": time.time() + 60},
        "test-secret",
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def _wait_for_completion(run_id: str, headers: dict, timeout: float = 2.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        resp = client.get(f"/runs/{run_id}", headers=headers)
        body = resp.json()
        if body["status"] in ("completed", "failed", "cancelled"):
            return body
        time.sleep(0.02)
    raise TimeoutError("run did not finish in time")


def test_save_prospect_from_completed_run():
    headers = _auth_header()
    run_resp = client.post(
        "/research",
        json={"full_name": "Jane Doe", "pasted_text": "Jane Doe\nSenior Engineer " * 5},
        headers=headers,
    )
    run_id = run_resp.json()["run_id"]
    _wait_for_completion(run_id, headers)

    save_resp = client.post("/prospects", json={"run_id": run_id}, headers=headers)
    assert save_resp.status_code == 201
    body = save_resp.json()
    assert body["full_name"] == "Jane Doe"
    assert body["source_run_id"] == run_id

    list_resp = client.get("/prospects", headers=headers)
    assert len(list_resp.json()) == 1


def test_save_prospect_rejects_incomplete_run():
    headers = _auth_header()
    run_resp = client.post(
        "/research",
        json={"linkedin_url": "https://linkedin.com/in/jane-doe"},
        headers=headers,
    )
    run_id = run_resp.json()["run_id"]
    _wait_for_completion(run_id, headers)  # this run fails (no provider for URL-only)

    save_resp = client.post("/prospects", json={"run_id": run_id}, headers=headers)
    assert save_resp.status_code == 409


def test_prospects_are_scoped_to_owner():
    headers_a = _auth_header("user-a")
    headers_b = _auth_header("user-b")
    run_resp = client.post(
        "/research",
        json={"full_name": "Jane Doe", "pasted_text": "Jane Doe\nEngineer " * 10},
        headers=headers_a,
    )
    run_id = run_resp.json()["run_id"]
    _wait_for_completion(run_id, headers_a)
    save_resp = client.post("/prospects", json={"run_id": run_id}, headers=headers_a)
    prospect_id = save_resp.json()["id"]

    assert client.get(f"/prospects/{prospect_id}", headers=headers_b).status_code == 404
    assert client.get(f"/prospects/{prospect_id}", headers=headers_a).status_code == 200
    assert client.get("/prospects", headers=headers_b).json() == []


def test_delete_prospect():
    headers = _auth_header()
    run_resp = client.post(
        "/research",
        json={"full_name": "Jane Doe", "pasted_text": "Jane Doe\nEngineer " * 10},
        headers=headers,
    )
    run_id = run_resp.json()["run_id"]
    _wait_for_completion(run_id, headers)
    save_resp = client.post("/prospects", json={"run_id": run_id}, headers=headers)
    prospect_id = save_resp.json()["id"]

    assert client.delete(f"/prospects/{prospect_id}", headers=headers).status_code == 204
    assert client.get(f"/prospects/{prospect_id}", headers=headers).status_code == 404
