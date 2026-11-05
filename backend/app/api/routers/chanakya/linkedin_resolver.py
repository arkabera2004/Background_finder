"""Agent 04 — LinkedIn Resolver: confirm identity or queue for human review."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.routers.chanakya.shared import get_run_or_404, person_to_dict
from app.core.auth import AuthenticatedUser, get_current_user
from app.core.config import settings
from app.db.chanakya_repository import ChanakyaRunRepository
from app.db.session import get_session
from app.providers.search_provider import build_search_provider
from app.schemas.chanakya import AgentName
from app.schemas.linkedin_resolver import ManualIdentityConfirmation
from app.services.linkedin_resolver import resolve_person_identity

router = APIRouter(prefix="/chanakya")


@router.post("/runs/{run_id}/linkedin-resolver", status_code=200)
async def run_linkedin_resolver(run_id: str, user: AuthenticatedUser = Depends(get_current_user)) -> dict:
    """Resolve every still-`pending` person on the run: exactly one search
    match confirms automatically, zero or multiple matches go to the
    manual review queue (`GET .../people/needs-review`) instead of
    guessing. Requires People Finder to have produced candidates first."""
    session = get_session()
    try:
        repo = ChanakyaRunRepository(session)
        run = get_run_or_404(repo, run_id, user.user_id)
        people = [p for p in repo.list_people(run_id) if p.resolution_status == "pending"]
        all_people = repo.list_people(run_id)
        if not all_people:
            raise HTTPException(
                status_code=409, detail="Run People Finder to produce candidates before LinkedIn Resolver"
            )

        repo.start_agent(run_id, AgentName.LINKEDIN_RESOLVER)
        try:
            search = build_search_provider(
                settings.search_provider, settings.tavily_api_key or None, settings.searxng_base_url or None
            )
            confirmed = ambiguous = unresolved = 0
            for person in people:
                company = next(c for c in run.scouted_companies if c.id == person.company_id)
                outcome = await resolve_person_identity(search, person.full_name, company.name)
                repo.apply_resolution(
                    person,
                    outcome["resolution_status"],
                    outcome["linkedin_url"],
                    outcome["candidate_profiles"],
                )
                if outcome["resolution_status"] == "confirmed":
                    confirmed += 1
                    repo.add_evidence(
                        run_id,
                        AgentName.LINKEDIN_RESOLVER,
                        entity_type="person",
                        entity_id=person.id,
                        source_url=outcome["linkedin_url"],
                        confidence=1.0,
                    )
                elif outcome["resolution_status"] == "ambiguous":
                    ambiguous += 1
                else:
                    unresolved += 1
        except Exception as exc:  # noqa: BLE001 - record and re-raise as a clean 502
            repo.fail_agent(run_id, AgentName.LINKEDIN_RESOLVER, str(exc))
            raise HTTPException(status_code=502, detail=f"LinkedIn Resolver failed: {exc}") from exc

        repo.complete_agent(
            run_id,
            AgentName.LINKEDIN_RESOLVER,
            {"processed": len(people), "confirmed": confirmed, "ambiguous": ambiguous, "unresolved": unresolved},
        )
        return {
            "processed": len(people),
            "confirmed": confirmed,
            "ambiguous": ambiguous,
            "unresolved": unresolved,
        }
    finally:
        session.close()


@router.get("/runs/{run_id}/people/needs-review")
async def list_people_needing_review(
    run_id: str, user: AuthenticatedUser = Depends(get_current_user)
) -> list[dict]:
    session = get_session()
    try:
        repo = ChanakyaRunRepository(session)
        get_run_or_404(repo, run_id, user.user_id)
        return [
            person_to_dict(p)
            for p in repo.list_people(run_id)
            if p.resolution_status in ("ambiguous", "unresolved")
        ]
    finally:
        session.close()


@router.post("/runs/{run_id}/people/{person_id}/resolve", status_code=200)
async def confirm_person_identity(
    run_id: str,
    person_id: str,
    payload: ManualIdentityConfirmation,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict:
    """Manual review queue resolution: a human picks the correct profile."""
    session = get_session()
    try:
        repo = ChanakyaRunRepository(session)
        get_run_or_404(repo, run_id, user.user_id)
        person = repo.get_person(person_id, run_id)
        if person is None:
            raise HTTPException(status_code=404, detail="Person not found")

        repo.confirm_person_manually(person, payload.linkedin_url)
        repo.add_evidence(
            run_id,
            AgentName.LINKEDIN_RESOLVER,
            entity_type="person",
            entity_id=person.id,
            source_url=payload.linkedin_url,
            confidence=1.0,
            excerpt="Manually confirmed by reviewer",
        )
        return person_to_dict(person)
    finally:
        session.close()
