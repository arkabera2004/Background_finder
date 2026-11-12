"""Agent 05 — Email Hunter: generate, verify, and decide on candidate emails."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.routers.chanakya.shared import email_candidate_to_dict, get_run_or_404
from app.core.auth import AuthenticatedUser, get_current_user
from app.core.config import settings
from app.db.chanakya_repository import ChanakyaRunRepository
from app.db.session import get_session
from app.providers.email_verification_provider import build_email_verification_provider
from app.schemas.chanakya import AgentName
from app.services.email_hunter import generate_candidate_emails, select_best_candidate, verify_candidates

router = APIRouter(prefix="/chanakya")


@router.post("/runs/{run_id}/email-hunter", status_code=200)
async def run_email_hunter(run_id: str, user: AuthenticatedUser = Depends(get_current_user)) -> dict:
    """For every confirmed person on the run, generate candidate addresses
    from their name + company domain, verify each (via the configured
    provider — "unknown" with none configured), and persist the result.
    Requires LinkedIn Resolver to have confirmed at least one person."""
    session = get_session()
    try:
        repo = ChanakyaRunRepository(session)
        run = get_run_or_404(repo, run_id, user.user_id)
        people = [p for p in repo.list_people(run_id) if p.identity_confirmed]
        if not people:
            raise HTTPException(
                status_code=409, detail="No confirmed people yet — run LinkedIn Resolver first"
            )

        repo.start_agent(run_id, AgentName.EMAIL_HUNTER)
        try:
            verifier = build_email_verification_provider(
                settings.email_verification_provider, settings.neverbounce_api_key or None
            )
            companies_by_id = {c.id: c for c in run.scouted_companies}
            found = []
            for person in people:
                company = companies_by_id.get(person.company_id)
                if company is None:
                    continue
                candidates = generate_candidate_emails(person.full_name, company.domain)
                verified = await verify_candidates(verifier, candidates)
                repo.upsert_email_candidates(run_id, user.user_id, person.id, verified)
                best = select_best_candidate(verified)
                if best is not None:
                    found.append((person, best))
                    repo.add_evidence(
                        run_id,
                        AgentName.EMAIL_HUNTER,
                        entity_type="email",
                        entity_id=person.id,
                        source_url=f"pattern:{best['pattern']}",
                        confidence=best["confidence"],
                    )
        except Exception as exc:  # noqa: BLE001 - record and re-raise as a clean 502
            repo.fail_agent(run_id, AgentName.EMAIL_HUNTER, f"{type(exc).__name__}: {exc}")
            raise HTTPException(status_code=502, detail=f"Email Hunter failed: {exc}") from exc

        repo.complete_agent(
            run_id,
            AgentName.EMAIL_HUNTER,
            {"people_processed": len(people), "emails_found": len(found)},
        )
        return {"people_processed": len(people), "emails_found": len(found)}
    finally:
        session.close()


@router.get("/runs/{run_id}/emails")
async def list_email_candidates(
    run_id: str, person_id: str | None = None, user: AuthenticatedUser = Depends(get_current_user)
) -> list[dict]:
    session = get_session()
    try:
        repo = ChanakyaRunRepository(session)
        get_run_or_404(repo, run_id, user.user_id)
        return [email_candidate_to_dict(c) for c in repo.list_email_candidates(run_id, person_id)]
    finally:
        session.close()


@router.get("/emails/needs-review")
async def list_risky_emails(user: AuthenticatedUser = Depends(get_current_user)) -> list[dict]:
    """Cross-run "Needs you" queue: every email candidate across all of
    the owner's runs that is a pattern guess, not a confirmed address."""
    session = get_session()
    try:
        repo = ChanakyaRunRepository(session)
        return [email_candidate_to_dict(c) for c in repo.list_risky_emails_for_owner(user.user_id)]
    finally:
        session.close()
