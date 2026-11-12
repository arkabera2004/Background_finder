"""Serializers and lookups shared across every Chanakya agent router.

Kept separate from any one agent's file so Catalogue/Company Scout/
People Finder/... stay independently readable — each agent file only
imports what it needs from here, never from a sibling agent file.
"""

from fastapi import HTTPException

from app.db.chanakya_models import (
    EmailCandidate,
    MonthlyRun,
    OfferingSnapshot,
    Person,
    QARecord,
    ResearchBrief,
    ScoutedCompany,
)
from app.db.chanakya_repository import ChanakyaRunRepository


def get_run_or_404(repo: ChanakyaRunRepository, run_id: str, owner_id: str) -> MonthlyRun:
    run = repo.get(run_id, owner_id=owner_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


def run_to_dict(run: MonthlyRun) -> dict:
    return {
        "id": run.id,
        "period": run.period,
        "status": run.status,
        "config": run.config,
        "created_at": run.created_at.isoformat(),
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "agent_executions": [
            {
                "agent_name": e.agent_name,
                "status": e.status,
                "retry_count": e.retry_count,
                "error": e.error,
                "output_summary": e.output_summary,
            }
            for e in run.agent_executions
        ],
    }


def snapshot_to_dict(snapshot: OfferingSnapshot) -> dict:
    return {
        "id": snapshot.id,
        "run_id": snapshot.run_id,
        "version": snapshot.version,
        "data": snapshot.data,
        "created_at": snapshot.created_at.isoformat(),
    }


def company_to_dict(company: ScoutedCompany) -> dict:
    return {
        "id": company.id,
        "run_id": company.run_id,
        "name": company.name,
        "domain": company.domain,
        "fit_score": company.fit_score,
        "selected": company.selected,
        "source_url": company.source_url,
        "created_at": company.created_at.isoformat(),
    }


def person_to_dict(person: Person) -> dict:
    return {
        "id": person.id,
        "run_id": person.run_id,
        "company_id": person.company_id,
        "company_name": person.company.name if person.company else None,
        "full_name": person.full_name,
        "role": person.role,
        "linkedin_url": person.linkedin_url,
        "confidence": person.confidence,
        "identity_confirmed": person.identity_confirmed,
        "resolution_status": person.resolution_status,
        "candidate_profiles": person.candidate_profiles,
        "created_at": person.created_at.isoformat(),
    }


def research_brief_to_dict(brief: ResearchBrief) -> dict:
    return {
        "id": brief.id,
        "run_id": brief.run_id,
        "person_id": brief.person_id,
        "status": brief.status,
        "data": brief.data,
        "created_at": brief.created_at.isoformat(),
    }


def qa_record_to_dict(record: QARecord) -> dict:
    return {
        "id": record.id,
        "run_id": record.run_id,
        "person_id": record.person_id,
        "person_name": record.person.full_name if record.person else None,
        "confidence_score": record.confidence_score,
        "confidence_level": record.confidence_level,
        "needs_review": record.needs_review,
        "draft_subject": record.draft_subject,
        "draft_body": record.draft_body,
        "approval_status": record.approval_status,
        "created_at": record.created_at.isoformat(),
    }


def email_candidate_to_dict(candidate: EmailCandidate) -> dict:
    return {
        "id": candidate.id,
        "run_id": candidate.run_id,
        "person_id": candidate.person_id,
        "person_name": candidate.person.full_name if candidate.person else None,
        "email": candidate.email,
        "pattern": candidate.pattern,
        "verification_status": candidate.verification_status,
        "confidence": candidate.confidence,
        "created_at": candidate.created_at.isoformat(),
    }
