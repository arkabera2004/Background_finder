import pytest
from sqlalchemy.orm import sessionmaker

from app.db.company_repository import CompanyRepository
from app.db.models import Company
from app.db.session import init_db, make_engine


@pytest.fixture
def session():
    engine = make_engine("sqlite:///:memory:")
    init_db(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    s = SessionLocal()
    yield s
    s.close()


def test_get_or_create_returns_existing_by_domain(session):
    repo = CompanyRepository(session)
    c1 = repo.get_or_create("user-1", "Acme Corp", "acme.com")
    c2 = repo.get_or_create("user-1", "ACME (different name)", "acme.com")

    assert c1.id == c2.id
    assert c2.name == "Acme Corp"  # unchanged


def test_get_or_create_creates_new_when_no_domain(session):
    repo = CompanyRepository(session)
    c1 = repo.get_or_create("user-1", "Generic LLC", None)
    c2 = repo.get_or_create("user-1", "Generic LLC", None)

    assert c1.id != c2.id  # different companies


def test_get_is_scoped_to_owner(session):
    repo = CompanyRepository(session)
    c = repo.get_or_create("user-a", "Acme", "acme.com")

    assert repo.get(c.id, owner_id="user-a") is not None
    assert repo.get(c.id, owner_id="user-b") is None


def test_list_for_owner_excludes_other_users(session):
    repo = CompanyRepository(session)
    repo.get_or_create("user-a", "Acme", "acme.com")
    repo.get_or_create("user-b", "TechCorp", "techcorp.com")

    assert len(repo.list_for_owner("user-a")) == 1
    assert repo.list_for_owner("user-a")[0].name == "Acme"


def test_delete(session):
    repo = CompanyRepository(session)
    c = repo.get_or_create("user-a", "Acme", "acme.com")

    assert repo.delete(c.id, owner_id="user-a") is True
    assert session.query(Company).filter(Company.id == c.id).one_or_none() is None


def test_update_research_data(session):
    repo = CompanyRepository(session)
    c = repo.get_or_create("user-a", "Acme", "acme.com")

    repo.update_research_data(c.id, "user-a", {"size": "1000+", "industry": "Tech"})
    updated = repo.get(c.id, "user-a")

    assert updated.data == {"size": "1000+", "industry": "Tech"}
