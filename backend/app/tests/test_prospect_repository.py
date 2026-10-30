import pytest
from sqlalchemy.orm import sessionmaker

from app.db.models import Brief, Prospect
from app.db.prospect_repository import ProspectRepository
from app.db.session import init_db, make_engine


@pytest.fixture
def session():
    """A real, isolated in-memory SQLite database per test — genuine DB
    roundtrips (insert, query, cascade delete), not a mock ORM."""
    engine = make_engine("sqlite:///:memory:")
    init_db(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    s = SessionLocal()
    yield s
    s.close()


def test_save_from_run_persists_prospect_and_brief(session):
    repo = ProspectRepository(session)
    prospect = repo.save_from_run(
        owner_id="user-1",
        full_name="Jane Doe",
        linkedin_url=None,
        run_id="run-123",
        brief_data={"prospect_name": "Jane Doe", "sources": []},
    )

    assert prospect.id is not None
    fetched = session.query(Prospect).filter(Prospect.id == prospect.id).one()
    assert fetched.full_name == "Jane Doe"
    assert fetched.source_run_id == "run-123"

    briefs = session.query(Brief).filter(Brief.prospect_id == prospect.id).all()
    assert len(briefs) == 1
    assert briefs[0].version == 1
    assert briefs[0].data["prospect_name"] == "Jane Doe"


def test_get_is_scoped_to_owner(session):
    repo = ProspectRepository(session)
    prospect = repo.save_from_run(
        owner_id="user-a",
        full_name="Jane Doe",
        linkedin_url=None,
        run_id="run-1",
        brief_data={"prospect_name": "Jane Doe"},
    )

    assert repo.get(prospect.id, owner_id="user-a") is not None
    assert repo.get(prospect.id, owner_id="user-b") is None


def test_list_for_owner_excludes_other_users(session):
    repo = ProspectRepository(session)
    repo.save_from_run("user-a", "Jane Doe", None, "run-1", {"prospect_name": "Jane Doe"})
    repo.save_from_run("user-b", "John Smith", None, "run-2", {"prospect_name": "John Smith"})

    assert len(repo.list_for_owner("user-a")) == 1
    assert repo.list_for_owner("user-a")[0].full_name == "Jane Doe"


def test_delete_cascades_to_briefs(session):
    repo = ProspectRepository(session)
    prospect = repo.save_from_run(
        "user-a", "Jane Doe", None, "run-1", {"prospect_name": "Jane Doe"}
    )

    assert repo.delete(prospect.id, owner_id="user-a") is True
    assert session.query(Prospect).filter(Prospect.id == prospect.id).one_or_none() is None
    assert session.query(Brief).filter(Brief.prospect_id == prospect.id).one_or_none() is None


def test_delete_returns_false_for_wrong_owner(session):
    repo = ProspectRepository(session)
    prospect = repo.save_from_run(
        "user-a", "Jane Doe", None, "run-1", {"prospect_name": "Jane Doe"}
    )
    assert repo.delete(prospect.id, owner_id="user-b") is False
