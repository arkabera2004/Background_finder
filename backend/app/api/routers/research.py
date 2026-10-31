import asyncio
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.core.auth import AuthenticatedUser, get_current_user
from app.db.memory_store import run_store
from app.schemas.research_request import ResearchRequest
from app.services.pdf_extract import PdfExtractionError, extract_text_from_pdf
from app.services.rate_limit import RateLimitExceededError, check_research_rate_limit
from app.services.research_service import check_identity_ambiguity, create_run, execute_run, select_identity

logger = logging.getLogger(__name__)

router = APIRouter()

_background_tasks: dict[str, asyncio.Task] = {}


def _run_to_dict(run) -> dict:
    return {
        "id": run.id,
        "status": run.status,
        "depth": run.depth,
        "steps": {
            name: {
                "status": step.status,
                "error": step.error,
                "started_at": step.started_at.isoformat() if step.started_at else None,
                "completed_at": step.completed_at.isoformat() if step.completed_at else None,
            }
            for name, step in run.steps.items()
        },
        "brief": run.brief,
        "created_at": run.created_at.isoformat(),
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "identity_candidates": run.identity_candidates,
    }


@router.post("/research", status_code=202)
async def create_research(
    req: ResearchRequest, user: AuthenticatedUser = Depends(get_current_user)
) -> dict:
    try:
        check_research_rate_limit(run_store, user.user_id)
    except RateLimitExceededError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc

    run = create_run(
        owner_id=user.user_id,
        depth=req.depth,
        full_name=req.full_name or "",
        linkedin_url=req.linkedin_url,
        company=req.company,
        pasted_text=req.pasted_text,
    )

    try:
        paused = await check_identity_ambiguity(run)
    except Exception as exc:
        logger.exception("Identity search failed for run %s", run.id)
        run_store.delete(run.id)
        raise HTTPException(
            status_code=502,
            detail="Could not reach the search provider to resolve this person's identity. "
            "Please try again, or provide a LinkedIn URL directly.",
        ) from exc
    if paused:
        return {"run_id": run.id, "status": run.status, "identity_candidates": run.identity_candidates}

    task = asyncio.create_task(execute_run(run))
    _background_tasks[run.id] = task
    return {"run_id": run.id, "status": run.status}


@router.post("/runs/{run_id}/select-identity")
async def select_run_identity(
    run_id: str, linkedin_url: str, user: AuthenticatedUser = Depends(get_current_user)
) -> dict:
    run = run_store.get(run_id, owner_id=user.user_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status != "needs_identity_selection":
        raise HTTPException(
            status_code=409, detail=f"Run is {run.status}, not awaiting identity selection"
        )
    valid_urls = {c["linkedin_url"] for c in run.identity_candidates}
    if linkedin_url not in valid_urls:
        raise HTTPException(status_code=422, detail="linkedin_url is not one of the offered candidates")

    select_identity(run, linkedin_url)
    task = asyncio.create_task(execute_run(run))
    _background_tasks[run.id] = task
    return {"run_id": run.id, "status": run.status}


@router.post("/research/pdf", status_code=202)
async def create_research_from_pdf(
    full_name: str,
    file: UploadFile,
    depth: str = "standard",
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict:
    try:
        check_research_rate_limit(run_store, user.user_id)
    except RateLimitExceededError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc

    data = await file.read()
    try:
        text = extract_text_from_pdf(data)
    except PdfExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    run = create_run(
        owner_id=user.user_id,
        depth=depth,
        full_name=full_name,
        linkedin_url=None,
        company=None,
        pasted_text=text,
    )
    task = asyncio.create_task(execute_run(run))
    _background_tasks[run.id] = task
    return {"run_id": run.id, "status": run.status}


@router.get("/runs/{run_id}")
async def get_run(run_id: str, user: AuthenticatedUser = Depends(get_current_user)) -> dict:
    run = run_store.get(run_id, owner_id=user.user_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return _run_to_dict(run)


@router.get("/runs/{run_id}/events")
async def stream_run_events(
    run_id: str, user: AuthenticatedUser = Depends(get_current_user)
):
    """Polling-based SSE: emits the run's current state every 300ms until
    it reaches a terminal status. Real Supabase Realtime/Redis pub-sub
    push-based events are NOT_STARTED (no infra running); this polls the
    same in-memory store GET /runs/{run_id} reads, so it's truthful, just
    not push-based."""
    run = run_store.get(run_id, owner_id=user.user_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    async def event_stream():
        last_payload = None
        while True:
            current = run_store.get(run_id, owner_id=user.user_id)
            if current is None:
                break
            payload = json.dumps(_run_to_dict(current))
            if payload != last_payload:
                yield f"data: {payload}\n\n"
                last_payload = payload
            if current.status in ("completed", "failed", "cancelled"):
                break
            await asyncio.sleep(0.3)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/runs/{run_id}/retry")
async def retry_run(run_id: str, user: AuthenticatedUser = Depends(get_current_user)) -> dict:
    """Re-runs the full pipeline for a failed run.

    LIMITATION: retries the whole run, not a single stage — true per-stage
    resume (reusing already-completed stage outputs) is NOT_STARTED.
    """
    run = run_store.get(run_id, owner_id=user.user_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status != "failed":
        raise HTTPException(status_code=409, detail=f"Run is {run.status}, not failed")

    run.status = "pending"
    run.cancel_requested = False
    for step in run.steps.values():
        step.status = "pending"
        step.error = None
        step.started_at = None
        step.completed_at = None

    task = asyncio.create_task(execute_run(run))
    _background_tasks[run.id] = task
    return {"run_id": run.id, "status": "retrying"}


@router.post("/runs/{run_id}/cancel")
async def cancel_run(run_id: str, user: AuthenticatedUser = Depends(get_current_user)) -> dict:
    run = run_store.get(run_id, owner_id=user.user_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    run.cancel_requested = True
    return {"run_id": run.id, "status": "cancel_requested"}
