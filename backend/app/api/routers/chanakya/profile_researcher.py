"""Agent 06 — Profile Researcher: a source-backed brief per confirmed leader."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.routers.chanakya.shared import get_run_or_404, research_brief_to_dict
from app.core.auth import AuthenticatedUser, get_current_user
from app.db.chanakya_repository import ChanakyaRunRepository
from app.db.session import get_session
from app.schemas.chanakya import AgentName
from app.services.profile_researcher import research_person

router = APIRouter(prefix="/chanakya")


@router.post("/runs/{run_id}/profile-researcher", status_code=200)
async def run_profile_researcher(run_id: str, user: AuthenticatedUser = Depends(get_current_user)) -> dict:
    """Drives the existing single-prospect research pipeline for every
    confirmed person on the run and persists its brief. A person whose
    pipeline run doesn't complete (provider failure, etc.) is recorded
    with that honest status, not a fabricated or partial brief. Requires
    LinkedIn Resolver to have confirmed at least one person first."""
    session = get_session()
    try:
        repo = ChanakyaRunRepository(session)
        run = get_run_or_404(repo, run_id, user.user_id)
        people = [p for p in repo.list_people(run_id) if p.identity_confirmed]
        if not people:
            raise HTTPException(
                status_code=409, detail="No confirmed people yet — run LinkedIn Resolver first"
            )

        repo.start_agent(run_id, AgentName.PROFILE_RESEARCHER)
        companies_by_id = {c.id: c for c in run.scouted_companies}
        completed = failed = 0
        for person in people:
            company = companies_by_id.get(person.company_id)
            if company is None or not person.linkedin_url:
                failed += 1
                continue
            outcome = await research_person(user.user_id, person.full_name, person.linkedin_url, company.name)
            repo.upsert_research_brief(run_id, user.user_id, person.id, outcome["status"], outcome["brief"] or {})
            if outcome["status"] == "completed":
                completed += 1
                for source in (outcome["brief"] or {}).get("sources", []):
                    repo.add_evidence(
                        run_id,
                        AgentName.PROFILE_RESEARCHER,
                        entity_type="person",
                        entity_id=person.id,
                        source_url=source.get("url", ""),
                        confidence=1.0,
                    )
            else:
                failed += 1

        repo.complete_agent(
            run_id,
            AgentName.PROFILE_RESEARCHER,
            {"people_processed": len(people), "completed": completed, "failed": failed},
        )
        return {"people_processed": len(people), "completed": completed, "failed": failed}
    finally:
        session.close()


@router.get("/runs/{run_id}/briefs")
async def list_research_briefs(
    run_id: str, person_id: str | None = None, user: AuthenticatedUser = Depends(get_current_user)
) -> list[dict]:
    session = get_session()
    try:
        repo = ChanakyaRunRepository(session)
        get_run_or_404(repo, run_id, user.user_id)
        return [research_brief_to_dict(b) for b in repo.list_research_briefs(run_id, person_id)]
    finally:
        session.close()
