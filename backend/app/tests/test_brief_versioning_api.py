import time

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.prospect_repository import ProspectRepository
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

    import app.api.routers.prospects as prospects_router

    monkeypatch.setattr(prospects_router, "get_session", lambda: _test_session_factory())
    monkeypatch.setattr(settings, "supabase_jwt_secret", "test-secret")


def _auth_header(user_id: str = "test-user") -> dict:
    token = jwt.encode(
        {"sub": user_id, "aud": "authenticated", "exp": time.time() + 60},
        "test-secret",
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def test_list_brief_versions_empty():
    response = client.get("/prospects/nonexistent/briefs", headers=_auth_header())
    assert response.status_code == 404


def test_list_brief_versions():
    headers = _auth_header()
    session = _test_session_factory()
    repo = ProspectRepository(session)

    prospect = repo.save_from_run(
        owner_id="test-user",
        full_name="Jane Doe",
        linkedin_url=None,
        run_id="run-1",
        brief_data={"prospect_name": "Jane Doe"},
    )
    prospect_id = prospect.id

    repo.add_brief_version(prospect_id, "test-user", {"prospect_name": "Jane Doe v2"}, "run-2")
    session.close()

    response = client.get(f"/prospects/{prospect_id}/briefs", headers=headers)

    assert response.status_code == 200
    versions = response.json()
    assert len(versions) == 2
    assert versions[0]["version"] == 1
    assert versions[1]["version"] == 2
    assert versions[0]["source_run_id"] == "run-1"
    assert versions[1]["source_run_id"] == "run-2"


def test_get_brief_version():
    headers = _auth_header()
    session = _test_session_factory()
    repo = ProspectRepository(session)

    prospect = repo.save_from_run(
        owner_id="test-user",
        full_name="Jane Doe",
        linkedin_url=None,
        run_id="run-1",
        brief_data={"prospect_name": "Jane Doe v1"},
    )
    prospect_id = prospect.id

    repo.add_brief_version(prospect_id, "test-user", {"prospect_name": "Jane Doe v2"})
    session.close()

    response = client.get(f"/prospects/{prospect_id}/briefs/2", headers=headers)

    assert response.status_code == 200
    brief = response.json()
    assert brief["prospect_name"] == "Jane Doe v2"


def test_get_brief_version_not_found():
    headers = _auth_header()
    session = _test_session_factory()
    repo = ProspectRepository(session)

    prospect = repo.save_from_run(
        owner_id="test-user",
        full_name="Jane Doe",
        linkedin_url=None,
        run_id="run-1",
        brief_data={},
    )
    prospect_id = prospect.id
    session.close()

    response = client.get(f"/prospects/{prospect_id}/briefs/999", headers=headers)

    assert response.status_code == 404


def test_list_brief_versions_cross_owner_returns_404():
    session = _test_session_factory()
    repo = ProspectRepository(session)

    prospect = repo.save_from_run(
        owner_id="owner-a",
        full_name="Jane Doe",
        linkedin_url=None,
        run_id="run-1",
        brief_data={"prospect_name": "Jane Doe"},
    )
    prospect_id = prospect.id
    session.close()

    response = client.get(f"/prospects/{prospect_id}/briefs", headers=_auth_header("owner-b"))

    assert response.status_code == 404


def test_get_brief_version_cross_owner_returns_404():
    session = _test_session_factory()
    repo = ProspectRepository(session)

    prospect = repo.save_from_run(
        owner_id="owner-a",
        full_name="Jane Doe",
        linkedin_url=None,
        run_id="run-1",
        brief_data={"prospect_name": "Jane Doe"},
    )
    prospect_id = prospect.id
    session.close()

    response = client.get(f"/prospects/{prospect_id}/briefs/1", headers=_auth_header("owner-b"))

    assert response.status_code == 404
