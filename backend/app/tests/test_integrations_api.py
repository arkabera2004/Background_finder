import time

from fastapi.testclient import TestClient
from jose import jwt

from app.core.config import settings
from main import app

client = TestClient(app)


def _auth_header(user_id: str = "test-user") -> dict:
    token = jwt.encode(
        {"sub": user_id, "aud": "authenticated", "exp": time.time() + 60},
        "test-secret",
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def test_list_integrations_requires_auth():
    response = client.get("/chanakya/integrations")
    assert response.status_code == 401


def test_list_integrations_reflects_active_search_provider(monkeypatch):
    monkeypatch.setattr(settings, "supabase_jwt_secret", "test-secret")
    monkeypatch.setattr(settings, "search_provider", "duckduckgo")
    monkeypatch.setattr(settings, "tavily_api_key", "real-key-not-printed")

    response = client.get("/chanakya/integrations", headers=_auth_header())

    assert response.status_code == 200
    body = response.json()
    by_name = {p["name"]: p for p in body}

    assert by_name["DuckDuckGo"]["status"] == "active"
    assert by_name["Tavily"]["status"] == "configured, not selected"
    # the real key value must never appear anywhere in the response
    assert "real-key-not-printed" not in response.text


def test_list_integrations_never_exposes_a_secret_value(monkeypatch):
    monkeypatch.setattr(settings, "supabase_jwt_secret", "test-secret")
    monkeypatch.setattr(settings, "gemini_api_key", "super-secret-value")

    response = client.get("/chanakya/integrations", headers=_auth_header())

    assert "super-secret-value" not in response.text
