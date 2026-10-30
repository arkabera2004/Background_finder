import pytest
from sqlalchemy.orm import sessionmaker

from app.db.models import Brief
from app.db.prospect_repository import ProspectRepository
from app.db.session import init_db, make_engine


@pytest.fixture
def session():
    engine = make_engine("sqlite:///:memory:")
    init_db(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    s = SessionLocal()
    yield s
    s.close()


def test_save_from_run_creates_version_1(session):
    repo = ProspectRepository(session)
    prospect = repo.save_from_run(
        owner_id="user-1",
        full_name="Jane Doe",
        linkedin_url="https://linkedin.com/in/janedoe",
        run_id="run-1",
        brief_data={"prospect_name": "Jane Doe", "snapshot": []},
    )

    assert len(prospect.briefs) == 1
    assert prospect.briefs[0].version == 1
    assert prospect.briefs[0].data == {"prospect_name": "Jane Doe", "snapshot": []}


def test_add_brief_version_creates_new_version(session):
    repo = ProspectRepository(session)
    prospect = repo.save_from_run(
        owner_id="user-1",
        full_name="Jane Doe",
        linkedin_url="https://linkedin.com/in/janedoe",
        run_id="run-1",
        brief_data={"prospect_name": "Jane Doe", "snapshot": []},
    )

    new_brief = repo.add_brief_version(
        prospect.id,
        owner_id="user-1",
        brief_data={"prospect_name": "Jane Doe", "snapshot": [{"text": "Senior Engineer"}]},
        run_id="run-2",
    )

    assert new_brief is not None
    assert new_brief.version == 2

    updated_prospect = repo.get(prospect.id, "user-1")
    assert len(updated_prospect.briefs) == 2
    assert max(b.version for b in updated_prospect.briefs) == 2


def test_get_brief_version_returns_specific_version(session):
    repo = ProspectRepository(session)
    prospect = repo.save_from_run(
        owner_id="user-1",
        full_name="Jane Doe",
        linkedin_url="https://linkedin.com/in/janedoe",
        run_id="run-1",
        brief_data={"prospect_name": "Jane Doe", "version": 1},
    )

    repo.add_brief_version(
        prospect.id,
        owner_id="user-1",
        brief_data={"prospect_name": "Jane Doe", "version": 2},
        run_id="run-2",
    )

    v1 = repo.get_brief_version(prospect.id, "user-1", version=1)
    v2 = repo.get_brief_version(prospect.id, "user-1", version=2)

    assert v1.version == 1
    assert v1.data["version"] == 1
    assert v2.version == 2
    assert v2.data["version"] == 2


def test_get_brief_version_none_returns_latest(session):
    repo = ProspectRepository(session)
    prospect = repo.save_from_run(
        owner_id="user-1",
        full_name="Jane Doe",
        linkedin_url="https://linkedin.com/in/janedoe",
        run_id="run-1",
        brief_data={"version": 1},
    )

    repo.add_brief_version(prospect.id, "user-1", {"version": 2})
    repo.add_brief_version(prospect.id, "user-1", {"version": 3})

    latest = repo.get_brief_version(prospect.id, "user-1", version=None)

    assert latest.version == 3
    assert latest.data["version"] == 3


def test_list_brief_versions_ordered(session):
    repo = ProspectRepository(session)
    prospect = repo.save_from_run(
        owner_id="user-1",
        full_name="Jane Doe",
        linkedin_url="https://linkedin.com/in/janedoe",
        run_id="run-1",
        brief_data={"v": 1},
    )

    repo.add_brief_version(prospect.id, "user-1", {"v": 2})
    repo.add_brief_version(prospect.id, "user-1", {"v": 3})

    versions = repo.list_brief_versions(prospect.id, "user-1")

    assert len(versions) == 3
    assert [v.version for v in versions] == [1, 2, 3]


def test_add_brief_version_owner_isolated(session):
    repo = ProspectRepository(session)
    prospect = repo.save_from_run(
        owner_id="user-a",
        full_name="Jane",
        linkedin_url=None,
        run_id="run-1",
        brief_data={},
    )

    # user-b cannot add a version to user-a's prospect
    result = repo.add_brief_version(prospect.id, "user-b", {})

    assert result is None

    # user-a can add
    result = repo.add_brief_version(prospect.id, "user-a", {})
    assert result is not None
