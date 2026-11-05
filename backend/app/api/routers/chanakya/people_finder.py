"""Agent 03 — People Finder: candidate leaders per selected company."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.routers.chanakya.shared import get_run_or_404, person_to_dict
from app.core.auth import AuthenticatedUser, get_current_user
from app.core.config import settings
from app.db.chanakya_models import Person
from app.db.chanakya_repository import ChanakyaRunRepository
from app.db.session import get_session
from app.providers.search_provider import build_search_provider
from app.schemas.chanakya import AgentName
from app.services.people_finder import discover_people_for_company, select_leaders

router = APIRouter(prefix="/chanakya")

DEFAULT_PEOPLE_PER_COMPANY = 4


@router.post("/runs/{run_id}/people-finder", status_code=200)
async def run_people_finder(run_id: str, user: AuthenticatedUser = Depends(get_current_user)) -> dict:
    """For each selected company, propose candidate leaders across
    priority roles. Never marks identity confirmed — that's Agent 04's
    job. Requires Company Scout to have selected companies first."""
    session = get_session()
    try:
        repo = ChanakyaRunRepository(session)
        run = get_run_or_404(repo, run_id, user.user_id)
        companies = repo.list_scouted_companies(run_id, selected_only=True)
        if not companies:
            raise HTTPException(
                status_code=409, detail="Run Company Scout and select companies before People Finder"
            )

        repo.start_agent(run_id, AgentName.PEOPLE_FINDER)
        people_per_company = run.config.get("people_per_company", DEFAULT_PEOPLE_PER_COMPANY)
        try:
            search = build_search_provider(
                settings.search_provider, settings.tavily_api_key or None, settings.searxng_base_url or None
            )
            total_selected: list[Person] = []
            for company in companies:
                candidates = await discover_people_for_company(search, company.name)
                leaders = select_leaders(candidates, people_per_company)
                persisted = repo.upsert_people(run_id, user.user_id, company.id, leaders)
                total_selected.extend(persisted)
                for person in persisted:
                    repo.add_evidence(
                        run_id,
                        AgentName.PEOPLE_FINDER,
                        entity_type="person",
                        entity_id=person.id,
                        source_url=person.linkedin_url or company.source_url,
                        confidence=person.confidence,
                    )
        except Exception as exc:  # noqa: BLE001 - record and re-raise as a clean 502
            repo.fail_agent(run_id, AgentName.PEOPLE_FINDER, str(exc))
            raise HTTPException(status_code=502, detail=f"People Finder failed: {exc}") from exc

        repo.complete_agent(
            run_id,
            AgentName.PEOPLE_FINDER,
            {"companies_processed": len(companies), "people_found": len(total_selected)},
        )
        return {
            "companies_processed": len(companies),
            "people": [person_to_dict(p) for p in total_selected],
        }
    finally:
        session.close()


@router.get("/runs/{run_id}/people")
async def list_people(
    run_id: str, company_id: str | None = None, user: AuthenticatedUser = Depends(get_current_user)
) -> list[dict]:
    session = get_session()
    try:
        repo = ChanakyaRunRepository(session)
        get_run_or_404(repo, run_id, user.user_id)
        return [person_to_dict(p) for p in repo.list_people(run_id, company_id)]
    finally:
        session.close()
