"""Agent 07 — QA and Sync: score, draft, route for approval, export."""

import csv
import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.api.routers.chanakya.shared import get_run_or_404, qa_record_to_dict
from app.core.auth import AuthenticatedUser, get_current_user
from app.db.chanakya_repository import ChanakyaRunRepository
from app.db.session import get_session
from app.schemas.chanakya import AgentName
from app.schemas.qa_sync import QAApprovalDecision
from app.services.qa_sync import draft_email, score_confidence

router = APIRouter(prefix="/chanakya")


@router.post("/runs/{run_id}/qa-sync", status_code=200)
async def run_qa_sync(run_id: str, user: AuthenticatedUser = Depends(get_current_user)) -> dict:
    """Scores every person on the run, drafts an outreach email from
    their research brief, and routes low-confidence records to manual
    review instead of hiding the uncertainty. Requires Profile Researcher
    to have produced at least one brief."""
    session = get_session()
    try:
        repo = ChanakyaRunRepository(session)
        run = get_run_or_404(repo, run_id, user.user_id)
        if not run.research_briefs:
            raise HTTPException(
                status_code=409, detail="No research briefs yet — run Profile Researcher first"
            )

        repo.start_agent(run_id, AgentName.QA_SYNC)
        offering_name = "our offering"
        if run.offering_snapshots:
            latest = max(run.offering_snapshots, key=lambda s: s.version)
            offerings = latest.data.get("offerings", [])
            if offerings:
                offering_name = offerings[0].get("name", offering_name)

        briefs_by_person = {b.person_id: b for b in run.research_briefs}
        emails_by_person: dict[str, list[str]] = {}
        for email in run.emails:
            emails_by_person.setdefault(email.person_id, []).append(email.verification_status)

        processed = flagged = 0
        for person in run.people:
            brief = briefs_by_person.get(person.id)
            scoring = score_confidence(
                person.identity_confirmed,
                emails_by_person.get(person.id, []),
                brief.status if brief else None,
            )
            draft = draft_email(person.full_name, offering_name, (brief.data if brief else {}) or {})
            repo.upsert_qa_record(
                run_id,
                user.user_id,
                person.id,
                scoring["score"],
                scoring["level"],
                scoring["needs_review"],
                draft["subject"],
                draft["body"],
            )
            processed += 1
            if scoring["needs_review"]:
                flagged += 1

        repo.complete_agent(
            run_id, AgentName.QA_SYNC, {"people_processed": processed, "needs_review": flagged}
        )
        return {"people_processed": processed, "needs_review": flagged}
    finally:
        session.close()


@router.get("/runs/{run_id}/qa")
async def list_qa_records(
    run_id: str, needs_review_only: bool = False, user: AuthenticatedUser = Depends(get_current_user)
) -> list[dict]:
    session = get_session()
    try:
        repo = ChanakyaRunRepository(session)
        get_run_or_404(repo, run_id, user.user_id)
        return [qa_record_to_dict(r) for r in repo.list_qa_records(run_id, needs_review_only)]
    finally:
        session.close()


@router.post("/runs/{run_id}/qa/{person_id}/approve", status_code=200)
async def approve_qa_record(
    run_id: str,
    person_id: str,
    payload: QAApprovalDecision,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict:
    """Human approval gate: this never sends anything — no send
    integration exists in this codebase — it only records the decision
    that a future, explicitly-authorized send step would require."""
    session = get_session()
    try:
        repo = ChanakyaRunRepository(session)
        get_run_or_404(repo, run_id, user.user_id)
        record = repo.get_qa_record(run_id, person_id)
        if record is None:
            raise HTTPException(status_code=404, detail="QA record not found for this person")
        repo.set_qa_approval(record, payload.approve)
        return qa_record_to_dict(record)
    finally:
        session.close()


@router.get("/runs/{run_id}/export")
async def export_run(
    run_id: str, format: str = "json", user: AuthenticatedUser = Depends(get_current_user)
):
    session = get_session()
    try:
        repo = ChanakyaRunRepository(session)
        run = get_run_or_404(repo, run_id, user.user_id)
        companies_by_id = {c.id: c for c in run.scouted_companies}
        rows = []
        for record in repo.list_qa_records(run_id):
            person = next((p for p in run.people if p.id == record.person_id), None)
            company = companies_by_id.get(person.company_id) if person else None
            rows.append(
                {
                    "company_name": company.name if company else "",
                    "company_domain": company.domain if company else "",
                    "person_name": person.full_name if person else "",
                    "role": person.role if person else "",
                    "linkedin_url": person.linkedin_url if person else "",
                    "confidence_level": record.confidence_level,
                    "approval_status": record.approval_status,
                    "draft_subject": record.draft_subject,
                }
            )

        if format == "csv":
            buffer = io.StringIO()
            fieldnames = list(rows[0].keys()) if rows else [
                "company_name", "company_domain", "person_name", "role",
                "linkedin_url", "confidence_level", "approval_status", "draft_subject",
            ]
            writer = csv.DictWriter(buffer, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
            return Response(
                content=buffer.getvalue(),
                media_type="text/csv",
                headers={"Content-Disposition": f'attachment; filename="run-{run_id}.csv"'},
            )
        return {"run_id": run_id, "rows": rows}
    finally:
        session.close()
