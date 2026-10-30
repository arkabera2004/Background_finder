import time

import pytest
from fastapi import HTTPException
from jose import jwt

from app.core import auth
from app.core.config import settings


class FakeRequest:
    def __init__(self, header: str | None):
        self.headers = {"Authorization": header} if header else {}


def _token(secret: str, **claims) -> str:
    payload = {"aud": "authenticated", "exp": time.time() + 60, **claims}
    return jwt.encode(payload, secret, algorithm="HS256")


def test_rejects_missing_header():
    with pytest.raises(HTTPException) as exc:
        auth.get_current_user(FakeRequest(None))
    assert exc.value.status_code == 401


def test_rejects_invalid_signature(monkeypatch):
    monkeypatch.setattr(settings, "supabase_jwt_secret", "real-secret")
    bad_token = _token("wrong-secret", sub="user-1")
    with pytest.raises(HTTPException) as exc:
        auth.get_current_user(FakeRequest(f"Bearer {bad_token}"))
    assert exc.value.status_code == 401


def test_accepts_valid_token(monkeypatch):
    monkeypatch.setattr(settings, "supabase_jwt_secret", "real-secret")
    token = _token("real-secret", sub="user-123", email="a@example.com")
    user = auth.get_current_user(FakeRequest(f"Bearer {token}"))
    assert user.user_id == "user-123"
    assert user.email == "a@example.com"
