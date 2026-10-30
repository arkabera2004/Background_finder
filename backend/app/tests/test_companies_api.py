import time

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.company_repository import CompanyRepository
from app.db.session import init_db, make_engine
from main import app

client = TestClient(app)

_test_engine = None
_test_session_factory = None


@pytest.fixture(autouse=True)
def _isolated_db(monkeypatch):
    """Each test gets its own fresh in-memory SQLite DB."""
    global _test_engine, _test_session_factory

    _test_engine = make_engine("sqlite:///:memory:")
    init_db(bind=_test_engine)
    _test_session_factory = sessionmaker(bind=_test_engine)

    import app.api.routers.companies as companies_router

    monkeypatch.setattr(companies_router, "get_session", lambda: _test_session_factory())
    monkeypatch.setattr(settings, "supabase_jwt_secret", "test-secret")


def _auth_header(user_id: str = "test-user") -> dict:
    token = jwt.encode(
        {"sub": user_id, "aud": "authenticated", "exp": time.time() + 60},
        "test-secret",
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def test_list_companies_empty():
    response = client.get("/companies", headers=_auth_header())

    assert response.status_code == 200
    assert response.json() == []


def test_list_companies_returns_user_companies():
    headers = _auth_header()
    session = _test_session_factory()
    repo = CompanyRepository(session)
    c1 = repo.get_or_create("test-user", "Acme", "acme.com")
    c2 = repo.get_or_create("test-user", "TechCorp", "techcorp.com")
    session.commit()

    response = client.get("/companies", headers=headers)

    assert response.status_code == 200
    companies = response.json()
    assert len(companies) == 2
    assert companies[0]["name"] == "TechCorp"  # order by created_at DESC
    assert companies[1]["name"] == "Acme"


def test_get_company_not_found():
    response = client.get("/companies/nonexistent", headers=_auth_header())

    assert response.status_code == 404


def test_get_company_returns_single_company():
    headers = _auth_header()
    session = _test_session_factory()
    repo = CompanyRepository(session)
    c = repo.get_or_create("test-user", "Acme", "acme.com")
    company_id = c.id
    session.commit()

    response = client.get(f"/companies/{company_id}", headers=headers)

    assert response.status_code == 200
    company = response.json()
    assert company["name"] == "Acme"
    assert company["domain"] == "acme.com"


def test_delete_company():
    headers = _auth_header()
    session = _test_session_factory()
    repo = CompanyRepository(session)
    c = repo.get_or_create("test-user", "Acme", "acme.com")
    company_id = c.id
    session.commit()

    response = client.delete(f"/companies/{company_id}", headers=headers)

    assert response.status_code == 204
    assert client.get(f"/companies/{company_id}", headers=headers).status_code == 404
