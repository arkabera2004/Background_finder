import httpx
from fastapi import HTTPException, Request
from jose import JWTError, jwt

from app.core.config import settings

# Supabase projects created/migrated after the JWT Signing Keys rollout sign
# session tokens asymmetrically (ES256/RS256) rather than with a single
# shared HS256 secret. The public keys are published, unauthenticated, at
# {SUPABASE_URL}/auth/v1/.well-known/jwks.json. Cached in-process and
# refreshed once if a token's `kid` isn't found (e.g. after key rotation).
_jwks_cache: dict | None = None


class AuthenticatedUser:
    def __init__(self, user_id: str, email: str | None):
        self.user_id = user_id
        self.email = email


def _fetch_jwks() -> dict:
    global _jwks_cache
    resp = httpx.get(f"{settings.supabase_url}/auth/v1/.well-known/jwks.json", timeout=10)
    resp.raise_for_status()
    jwks: dict = resp.json()
    _jwks_cache = jwks
    return jwks


def _find_jwk(kid: str) -> dict | None:
    jwks = _jwks_cache or _fetch_jwks()
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key
    # kid not in cache — key may have rotated; refresh once and retry.
    jwks = _fetch_jwks()
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key
    return None


def get_current_user(request: Request) -> AuthenticatedUser:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = header.removeprefix("Bearer ")

    try:
        unverified_header = jwt.get_unverified_header(token)
        alg = unverified_header.get("alg", "HS256")

        if alg == "HS256":
            payload = jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
            )
        else:
            jwk = _find_jwk(unverified_header.get("kid", ""))
            if jwk is None:
                raise HTTPException(status_code=401, detail="Unknown signing key")
            payload = jwt.decode(token, jwk, algorithms=[alg], audience="authenticated")
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=401, detail="Could not verify token signature") from exc

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing subject claim")

    return AuthenticatedUser(user_id=user_id, email=payload.get("email"))
