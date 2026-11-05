"""Phase 9 — Orchestration: drive Agents 02-07 in sequence, resumably.

Agent 01 (Catalogue) is deliberately excluded — the master prompt's
workflow step 2 is "load and approve the monthly offerings," a human
action, not something to auto-trigger. Everything downstream of an
approved offering brief can run unattended.

There is no queue/scheduler here yet (that's the remaining Phase 9 gap,
documented in docs/PHASE_TRACKER.md) — this is a single endpoint that
calls each agent's existing, already-idempotent handler in order. Each
agent only does real work when its own AgentExecution isn't already
COMPLETED (every agent's upsert methods were built idempotent from
Phase 1 onward), so calling this endpoint again after a failure resumes
from the failed stage instead of redoing finished work or duplicating
records.
"""

from collections.abc import Awaitable, Callable

from fastapi import APIRouter, Depends, HTTPException

from app.api.routers.chanakya import (
    company_scout,
    email_hunter,
    linkedin_resolver,
    people_finder,
    profile_researcher,
    qa_sync,
)
from app.api.routers.chanakya.shared import get_run_or_404
from app.core.auth import AuthenticatedUser, get_current_user
from app.db.chanakya_repository import ChanakyaRunRepository
from app.db.session import get_session
from app.schemas.chanakya import AgentExecutionStatus, AgentName

router = APIRouter(prefix="/chanakya")

AgentHandler = Callable[[str, AuthenticatedUser], Awaitable[dict]]

# Agent 01 (Catalogue) isn't here — see module docstring.
ORCHESTRATED_STAGES: list[tuple[AgentName, AgentHandler]] = [
    (AgentName.COMPANY_SCOUT, company_scout.run_company_scout),
    (AgentName.PEOPLE_FINDER, people_finder.run_people_finder),
    (AgentName.LINKEDIN_RESOLVER, linkedin_resolver.run_linkedin_resolver),
    (AgentName.EMAIL_HUNTER, email_hunter.run_email_hunter),
    (AgentName.PROFILE_RESEARCHER, profile_researcher.run_profile_researcher),
    (AgentName.QA_SYNC, qa_sync.run_qa_sync),
]


@router.post("/runs/{run_id}/orchestrate", status_code=200)
async def orchestrate_run(run_id: str, user: AuthenticatedUser = Depends(get_current_user)) -> dict:
    session = get_session()
    try:
        repo = ChanakyaRunRepository(session)
        get_run_or_404(repo, run_id, user.user_id)

        stages: list[dict] = []
        stopped_at: str | None = None
        for agent_name, handler in ORCHESTRATED_STAGES:
            run = get_run_or_404(repo, run_id, user.user_id)
            execution = next(e for e in run.agent_executions if e.agent_name == agent_name.value)
            if execution.status == AgentExecutionStatus.COMPLETED.value:
                stages.append({"agent": agent_name.value, "status": "skipped_already_completed"})
                continue

            try:
                result = await handler(run_id, user)
                stages.append({"agent": agent_name.value, "status": "completed", "result": result})
            except HTTPException as exc:
                stages.append(
                    {"agent": agent_name.value, "status": "stopped", "error": str(exc.detail)}
                )
                stopped_at = agent_name.value
                break

        return {"run_id": run_id, "stages": stages, "stopped_at": stopped_at}
    finally:
        session.close()
