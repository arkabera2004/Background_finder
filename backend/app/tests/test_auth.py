import time

import httpx
import pytest
from fastapi import HTTPException
from jose import jwt
from jose.backends.cryptography_backend import CryptographyECKey

from app.core import auth
from app.core.config import settings


class FakeRequest:
    def __init__(self, header: str | None):
        self.headers = {"Authorization": header} if header else {}


def _token(secret: str, **claims) -> str:
    payload = {"aud": "authenticated", "exp": time.time() + 60, **claims}
    return jwt.encode(payload, secret, algorithm="HS256")


def _ec_keypair(kid: str):
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.asymmetric import ec

    private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    full_jwk = CryptographyECKey(private_key, algorithm="ES256").to_dict()
    public_jwk = {k: v for k, v in full_jwk.items() if k != "d"}
    public_jwk["kid"] = kid
    return full_jwk, public_jwk


class _FakeJwksResponse:
    def __init__(self, keys: list[dict]):
        self._payload = {"keys": keys}
        self.status_code = 200

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        pass


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


def test_accepts_valid_asymmetric_token_via_jwks(monkeypatch):
    """Covers Supabase projects migrated to JWT Signing Keys (ES256), where
    there is no shared secret at all — verification must use the public
    key published at {SUPABASE_URL}/auth/v1/.well-known/jwks.json."""
    full_jwk, public_jwk = _ec_keypair(kid="kid-1")
    monkeypatch.setattr(auth, "_jwks_cache", None)
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeJwksResponse([public_jwk]))

    payload = {
        "aud": "authenticated",
        "exp": time.time() + 60,
        "sub": "user-456",
        "email": "b@example.com",
    }
    token = jwt.encode(payload, full_jwk, algorithm="ES256", headers={"kid": "kid-1"})

    user = auth.get_current_user(FakeRequest(f"Bearer {token}"))
    assert user.user_id == "user-456"
    assert user.email == "b@example.com"


def test_rejects_asymmetric_token_with_unknown_kid(monkeypatch):
    full_jwk, public_jwk = _ec_keypair(kid="kid-1")
    monkeypatch.setattr(auth, "_jwks_cache", None)
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeJwksResponse([public_jwk]))

    token = jwt.encode(
        {"aud": "authenticated", "exp": time.time() + 60, "sub": "user-1"},
        full_jwk,
        algorithm="ES256",
        headers={"kid": "kid-rotated-away"},
    )

    with pytest.raises(HTTPException) as exc:
        auth.get_current_user(FakeRequest(f"Bearer {token}"))
    assert exc.value.status_code == 401


def test_rejects_asymmetric_token_when_jwks_fetch_fails(monkeypatch):
    full_jwk, _public_jwk = _ec_keypair(kid="kid-1")
    monkeypatch.setattr(auth, "_jwks_cache", None)

    def _raise(*_a, **_k):
        raise httpx.ConnectError("jwks unreachable")

    monkeypatch.setattr(httpx, "get", _raise)

    token = jwt.encode(
        {"aud": "authenticated", "exp": time.time() + 60, "sub": "user-1"},
        full_jwk,
        algorithm="ES256",
        headers={"kid": "kid-1"},
    )

    with pytest.raises(HTTPException) as exc:
        auth.get_current_user(FakeRequest(f"Bearer {token}"))
    assert exc.value.status_code == 401
