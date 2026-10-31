import asyncio
import time

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.core.config import settings
from main import app

client = TestClient(app)


def _auth_header(user_id: str = "user-1") -> dict:
    token = jwt.encode(
        {"sub": user_id, "aud": "authenticated", "exp": time.time() + 60},
        settings.supabase_jwt_secret or "test-secret",
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def _secret(monkeypatch):
    monkeypatch.setattr(settings, "supabase_jwt_secret", "test-secret")


def _wait_for_completion(run_id: str, headers: dict, timeout: float = 2.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        resp = client.get(f"/runs/{run_id}", headers=headers)
        body = resp.json()
        if body["status"] in ("completed", "failed", "cancelled"):
            return body
        time.sleep(0.02)
    raise TimeoutError("run did not finish in time")


def test_create_research_requires_auth():
    resp = client.post("/research", json={"full_name": "Jane Doe", "company": "Acme"})
    assert resp.status_code == 401


def test_create_research_rejects_invalid_input():
    resp = client.post("/research", json={}, headers=_auth_header())
    assert resp.status_code == 422


def test_create_research_completes_via_pasted_text():
    headers = _auth_header()
    resp = client.post(
        "/research",
        json={"full_name": "Jane Doe", "pasted_text": "Jane Doe\nSenior Engineer at Acme " * 3},
        headers=headers,
    )
    assert resp.status_code == 202
    run_id = resp.json()["run_id"]

    final = _wait_for_completion(run_id, headers)
    assert final["status"] == "completed"
    assert final["brief"]["prospect_name"] == "Jane Doe"
    assert all(s["status"] == "completed" for s in final["steps"].values())


def test_get_run_is_scoped_to_owner():
    headers_a = _auth_header("user-a")
    headers_b = _auth_header("user-b")
    resp = client.post(
        "/research",
        json={"full_name": "Jane Doe", "pasted_text": "Jane Doe\nEngineer " * 10},
        headers=headers_a,
    )
    run_id = resp.json()["run_id"]

    assert client.get(f"/runs/{run_id}", headers=headers_b).status_code == 404
    assert client.get(f"/runs/{run_id}", headers=headers_a).status_code == 200


def test_cancel_unknown_run_returns_404():
    resp = client.post("/runs/does-not-exist/cancel", headers=_auth_header())
    assert resp.status_code == 404


def test_retry_requires_failed_status():
    headers = _auth_header()
    resp = client.post(
        "/research",
        json={"full_name": "Jane Doe", "pasted_text": "Jane Doe\nEngineer " * 10},
        headers=headers,
    )
    run_id = resp.json()["run_id"]
    _wait_for_completion(run_id, headers)

    retry_resp = client.post(f"/runs/{run_id}/retry", headers=headers)
    assert retry_resp.status_code == 409


def test_create_research_rate_limited_after_daily_cap():
    from app.db.memory_store import run_store

    headers = _auth_header("rate-limited-user")
    for _ in range(30):
        run_store.create(owner_id="rate-limited-user", depth="standard")

    resp = client.post(
        "/research",
        json={"full_name": "Jane Doe", "pasted_text": "Jane Doe\nEngineer " * 10},
        headers=headers,
    )
    assert resp.status_code == 429


def test_create_research_fails_for_url_only_without_provider():
    headers = _auth_header()
    resp = client.post(
        "/research", json={"linkedin_url": "https://linkedin.com/in/jane-doe"}, headers=headers
    )
    assert resp.status_code == 202
    run_id = resp.json()["run_id"]

    final = _wait_for_completion(run_id, headers)
    assert final["status"] == "failed"
    assert final["steps"]["fetch_profile"]["status"] == "failed"
