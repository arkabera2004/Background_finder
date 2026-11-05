import pytest
from sqlalchemy.orm import sessionmaker

import app.db.chanakya_models  # noqa: F401 - registers tables with Base.metadata
from app.db.chanakya_repository import ChanakyaRunRepository
from app.db.session import init_db, make_engine
from app.schemas.chanakya import AgentExecutionStatus, AgentName, RunStatus


@pytest.fixture
def session():
    engine = make_engine("sqlite:///:memory:")
    init_db(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    s = SessionLocal()
    yield s
    s.close()


def test_create_run_seeds_one_execution_row_per_agent(session):
    repo = ChanakyaRunRepository(session)
    run = repo.create_run("user-1", "2026-11")

    assert run.status == RunStatus.PENDING.value
    assert len(run.agent_executions) == len(list(AgentName))
    assert {e.agent_name for e in run.agent_executions} == {a.value for a in AgentName}
    assert all(e.status == AgentExecutionStatus.PENDING.value for e in run.agent_executions)


def test_get_and_list_are_owner_scoped(session):
    repo = ChanakyaRunRepository(session)
    run = repo.create_run("user-a", "2026-11")
    repo.create_run("user-b", "2026-11")

    assert repo.get(run.id, owner_id="user-a") is not None
    assert repo.get(run.id, owner_id="user-b") is None
    assert len(repo.list_for_owner("user-a")) == 1


def test_offering_snapshots_are_versioned_and_append_only(session):
    repo = ChanakyaRunRepository(session)
    run = repo.create_run("user-a", "2026-11")

    s1 = repo.add_offering_snapshot(run, {"offerings": ["accelerator-a"]})
    s2 = repo.add_offering_snapshot(run, {"offerings": ["accelerator-a", "accelerator-b"]})

    assert s1.version == 1
    assert s2.version == 2
    # the first snapshot is untouched by the second write
    assert s1.data == {"offerings": ["accelerator-a"]}


def test_agent_lifecycle_start_complete_fail(session):
    repo = ChanakyaRunRepository(session)
    run = repo.create_run("user-a", "2026-11")

    started = repo.start_agent(run.id, AgentName.COMPANY_SCOUT)
    assert started.status == AgentExecutionStatus.RUNNING.value
    assert started.started_at is not None

    completed = repo.complete_agent(run.id, AgentName.COMPANY_SCOUT, {"companies_found": 100})
    assert completed.status == AgentExecutionStatus.COMPLETED.value
    assert completed.output_summary == {"companies_found": 100}
    assert completed.completed_at is not None

    failed = repo.fail_agent(run.id, AgentName.EMAIL_HUNTER, "provider timeout")
    assert failed.status == AgentExecutionStatus.FAILED.value
    assert failed.retry_count == 1
    assert failed.error == "provider timeout"


def test_start_agent_is_idempotent_once_completed():
    """A resumed/retried run must not redo a stage that already finished."""
    engine = make_engine("sqlite:///:memory:")
    init_db(bind=engine)
    session = sessionmaker(bind=engine)()
    repo = ChanakyaRunRepository(session)
    run = repo.create_run("user-a", "2026-11")

    repo.start_agent(run.id, AgentName.CATALOGUE)
    completed = repo.complete_agent(run.id, AgentName.CATALOGUE, {"offerings": 3})

    # Re-starting the same agent after completion must not reset its output/status.
    re_started = repo.start_agent(run.id, AgentName.CATALOGUE)
    assert re_started.status == AgentExecutionStatus.COMPLETED.value
    assert re_started.output_summary == {"offerings": 3}
    assert re_started.id == completed.id
    session.close()


def test_evidence_records_provenance_per_entity(session):
    repo = ChanakyaRunRepository(session)
    run = repo.create_run("user-a", "2026-11")

    repo.add_evidence(
        run.id,
        AgentName.COMPANY_SCOUT,
        entity_type="company",
        entity_id="company-123",
        source_url="https://example.com/about",
        confidence=0.9,
        excerpt="Acme Corp is a 500-person fintech company.",
    )

    rows = run.evidence
    assert len(rows) == 1
    assert rows[0].entity_type == "company"
    assert rows[0].entity_id == "company-123"
    assert rows[0].confidence == 0.9


def test_upsert_scouted_companies_dedupes_by_domain(session):
    repo = ChanakyaRunRepository(session)
    run = repo.create_run("user-a", "2026-11")

    repo.upsert_scouted_companies(
        run.id,
        "user-a",
        [{"name": "Acme", "domain": "acme.com", "source_url": "https://acme.com", "fit_score": 0.5}],
    )
    updated = repo.upsert_scouted_companies(
        run.id,
        "user-a",
        [{"name": "Acme Corp", "domain": "acme.com", "source_url": "https://acme.com/about", "fit_score": 0.9}],
    )

    assert len(updated) == 1
    assert updated[0].name == "Acme Corp"
    assert updated[0].fit_score == 0.9
    assert len(repo.list_scouted_companies(run.id)) == 1


def test_select_top_companies_marks_selected_and_is_idempotent(session):
    repo = ChanakyaRunRepository(session)
    run = repo.create_run("user-a", "2026-11")
    repo.upsert_scouted_companies(
        run.id,
        "user-a",
        [
            {"name": "A", "domain": "a.com", "source_url": "https://a.com", "fit_score": 0.2},
            {"name": "B", "domain": "b.com", "source_url": "https://b.com", "fit_score": 0.9},
            {"name": "C", "domain": "c.com", "source_url": "https://c.com", "fit_score": 0.5},
        ],
    )

    selected = repo.select_top_companies(run.id, 2)
    assert {c.domain for c in selected} == {"b.com", "c.com"}
    assert {c.domain for c in repo.list_scouted_companies(run.id, selected_only=True)} == {"b.com", "c.com"}

    # re-running with a smaller target clears the previous selection rather than adding to it
    reselected = repo.select_top_companies(run.id, 1)
    assert {c.domain for c in reselected} == {"b.com"}
    assert {c.domain for c in repo.list_scouted_companies(run.id, selected_only=True)} == {"b.com"}


def test_upsert_people_dedupes_by_full_name_within_company(session):
    repo = ChanakyaRunRepository(session)
    run = repo.create_run("user-a", "2026-11")
    [company] = repo.upsert_scouted_companies(
        run.id, "user-a", [{"name": "Acme", "domain": "acme.com", "source_url": "https://acme.com", "fit_score": 1.0}]
    )

    repo.upsert_people(
        run.id,
        "user-a",
        company.id,
        [{"full_name": "Jane Doe", "role": "CEO", "linkedin_url": "https://linkedin.com/in/jane", "confidence": 0.8}],
    )
    updated = repo.upsert_people(
        run.id,
        "user-a",
        company.id,
        [{"full_name": "Jane Doe", "role": "Founder & CEO", "linkedin_url": "https://linkedin.com/in/jane", "confidence": 0.95}],
    )

    assert len(updated) == 1
    assert updated[0].role == "Founder & CEO"
    assert updated[0].confidence == 0.95
    assert updated[0].identity_confirmed is False
    assert len(repo.list_people(run.id)) == 1
    assert len(repo.list_people(run.id, company_id=company.id)) == 1


def test_apply_resolution_confirmed_sets_linkedin_url_and_identity_confirmed(session):
    repo = ChanakyaRunRepository(session)
    run = repo.create_run("user-a", "2026-11")
    [company] = repo.upsert_scouted_companies(
        run.id, "user-a", [{"name": "Acme", "domain": "acme.com", "source_url": "https://acme.com", "fit_score": 1.0}]
    )
    [person] = repo.upsert_people(
        run.id, "user-a", company.id, [{"full_name": "Jane Doe", "role": "CEO", "linkedin_url": None, "confidence": 0.5}]
    )

    repo.apply_resolution(
        person, "confirmed", "https://linkedin.com/in/janedoe", [{"linkedin_url": "https://linkedin.com/in/janedoe"}]
    )

    assert person.resolution_status == "confirmed"
    assert person.linkedin_url == "https://linkedin.com/in/janedoe"
    assert person.identity_confirmed is True


def test_apply_resolution_ambiguous_does_not_confirm_identity(session):
    repo = ChanakyaRunRepository(session)
    run = repo.create_run("user-a", "2026-11")
    [company] = repo.upsert_scouted_companies(
        run.id, "user-a", [{"name": "Acme", "domain": "acme.com", "source_url": "https://acme.com", "fit_score": 1.0}]
    )
    [person] = repo.upsert_people(
        run.id, "user-a", company.id, [{"full_name": "Jane Doe", "role": "CEO", "linkedin_url": None, "confidence": 0.5}]
    )

    repo.apply_resolution(person, "ambiguous", None, [{"linkedin_url": "a"}, {"linkedin_url": "b"}])

    assert person.resolution_status == "ambiguous"
    assert person.identity_confirmed is False
    assert person.linkedin_url is None
    assert len(person.candidate_profiles) == 2


def test_confirm_person_manually_overrides_ambiguous_state(session):
    repo = ChanakyaRunRepository(session)
    run = repo.create_run("user-a", "2026-11")
    [company] = repo.upsert_scouted_companies(
        run.id, "user-a", [{"name": "Acme", "domain": "acme.com", "source_url": "https://acme.com", "fit_score": 1.0}]
    )
    [person] = repo.upsert_people(
        run.id, "user-a", company.id, [{"full_name": "Jane Doe", "role": "CEO", "linkedin_url": None, "confidence": 0.5}]
    )
    repo.apply_resolution(person, "ambiguous", None, [{"linkedin_url": "a"}, {"linkedin_url": "b"}])

    repo.confirm_person_manually(person, "https://linkedin.com/in/janedoe")

    assert person.resolution_status == "confirmed"
    assert person.identity_confirmed is True
    assert person.linkedin_url == "https://linkedin.com/in/janedoe"


def test_upsert_email_candidates_dedupes_by_email(session):
    repo = ChanakyaRunRepository(session)
    run = repo.create_run("user-a", "2026-11")
    [company] = repo.upsert_scouted_companies(
        run.id, "user-a", [{"name": "Acme", "domain": "acme.com", "source_url": "https://acme.com", "fit_score": 1.0}]
    )
    [person] = repo.upsert_people(
        run.id, "user-a", company.id, [{"full_name": "Jane Doe", "role": "CEO", "linkedin_url": None, "confidence": 0.5}]
    )

    repo.upsert_email_candidates(
        run.id,
        "user-a",
        person.id,
        [{"email": "jane.doe@acme.com", "pattern": "first.last", "verification_status": "needs_review", "confidence": 0.0}],
    )
    updated = repo.upsert_email_candidates(
        run.id,
        "user-a",
        person.id,
        [{"email": "jane.doe@acme.com", "pattern": "first.last", "verification_status": "valid", "confidence": 0.9}],
    )

    assert len(updated) == 1
    assert updated[0].verification_status == "valid"
    assert len(repo.list_email_candidates(run.id)) == 1
    assert len(repo.list_email_candidates(run.id, person_id=person.id)) == 1


def test_upsert_research_brief_replaces_on_rerun(session):
    repo = ChanakyaRunRepository(session)
    run = repo.create_run("user-a", "2026-11")
    [company] = repo.upsert_scouted_companies(
        run.id, "user-a", [{"name": "Acme", "domain": "acme.com", "source_url": "https://acme.com", "fit_score": 1.0}]
    )
    [person] = repo.upsert_people(
        run.id, "user-a", company.id, [{"full_name": "Jane Doe", "role": "CEO", "linkedin_url": None, "confidence": 0.5}]
    )

    repo.upsert_research_brief(run.id, "user-a", person.id, "failed", {})
    updated = repo.upsert_research_brief(run.id, "user-a", person.id, "completed", {"career": ["CEO at Acme"]})

    assert updated.status == "completed"
    assert updated.data == {"career": ["CEO at Acme"]}
    assert len(repo.list_research_briefs(run.id)) == 1
    assert len(repo.list_research_briefs(run.id, person_id=person.id)) == 1


def test_mark_run_status_sets_completed_at(session):
    repo = ChanakyaRunRepository(session)
    run = repo.create_run("user-a", "2026-11")

    repo.mark_run_status(run, RunStatus.COMPLETED)

    assert run.status == RunStatus.COMPLETED.value
    assert run.completed_at is not None
