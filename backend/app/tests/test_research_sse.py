import time

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.core.config import settings
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


def test_sse_stream_ends_in_terminal_state():
    headers = _auth_header()
    resp = client.post(
        "/research",
        json={"full_name": "Jane Doe", "pasted_text": "Jane Doe\nEngineer " * 10},
        headers=headers,
    )
    run_id = resp.json()["run_id"]

    with client.stream("GET", f"/runs/{run_id}/events", headers=headers) as stream:
        events = [line for line in stream.iter_lines() if line.startswith("data:")]

    assert len(events) >= 1
    assert '"completed"' in events[-1] or '"status": "completed"' in events[-1]


def test_sse_unknown_run_returns_404():
    resp = client.get("/runs/nope/events", headers=_auth_header())
    assert resp.status_code == 404
