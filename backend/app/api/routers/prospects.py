from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from app.core.auth import AuthenticatedUser, get_current_user
from app.db.memory_store import run_store
from app.db.prospect_repository import ProspectRepository
from app.db.session import get_session
from app.services.brief_export import to_json, to_markdown, to_pdf

router = APIRouter()


class SaveProspectRequest(BaseModel):
    run_id: str


def _prospect_to_dict(prospect, brief: dict | None = None) -> dict:
    return {
        "id": prospect.id,
        "full_name": prospect.full_name,
        "linkedin_url": prospect.linkedin_url,
        "tags": prospect.tags,
        "status": prospect.status,
        "source_run_id": prospect.source_run_id,
        "created_at": prospect.created_at.isoformat(),
        "brief": brief,
    }


@router.post("/prospects", status_code=201)
async def save_prospect(
    req: SaveProspectRequest, user: AuthenticatedUser = Depends(get_current_user)
) -> dict:
    """Explicitly promotes a completed run into a saved Prospect. Never
    automatic — a user must call this after reviewing the run's brief."""
    run = run_store.get(req.run_id, owner_id=user.user_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status != "completed" or run.brief is None:
        raise HTTPException(status_code=409, detail="Run has no completed brief to save")

    session = get_session()
    try:
        repo = ProspectRepository(session)
        prospect = repo.save_from_run(
            owner_id=user.user_id,
            full_name=run.brief.get("prospect_name", run.full_name),
            linkedin_url=run.linkedin_url,
            run_id=run.id,
            brief_data=run.brief,
        )
        return _prospect_to_dict(prospect, run.brief)
    finally:
        session.close()


@router.get("/prospects")
async def list_prospects(user: AuthenticatedUser = Depends(get_current_user)) -> list[dict]:
    session = get_session()
    try:
        repo = ProspectRepository(session)
        return [_prospect_to_dict(p) for p in repo.list_for_owner(user.user_id)]
    finally:
        session.close()


@router.get("/prospects/{prospect_id}")
async def get_prospect(
    prospect_id: str, user: AuthenticatedUser = Depends(get_current_user)
) -> dict:
    session = get_session()
    try:
        repo = ProspectRepository(session)
        prospect = repo.get(prospect_id, owner_id=user.user_id)
        if prospect is None:
            raise HTTPException(status_code=404, detail="Prospect not found")
        latest_brief = max(prospect.briefs, key=lambda b: b.version).data if prospect.briefs else None
        return _prospect_to_dict(prospect, latest_brief)
    finally:
        session.close()


@router.get("/prospects/{prospect_id}/brief/export")
async def export_brief(
    prospect_id: str,
    format: str = "json",
    user: AuthenticatedUser = Depends(get_current_user),
) -> Response:
    if format not in ("json", "md", "pdf"):
        raise HTTPException(status_code=422, detail="format must be one of: json, md, pdf")

    session = get_session()
    try:
        repo = ProspectRepository(session)
        prospect = repo.get(prospect_id, owner_id=user.user_id)
        if prospect is None or not prospect.briefs:
            raise HTTPException(status_code=404, detail="Prospect or brief not found")
        latest_brief = max(prospect.briefs, key=lambda b: b.version).data

        if format == "json":
            return Response(content=to_json(latest_brief), media_type="application/json")
        if format == "md":
            return Response(content=to_markdown(latest_brief), media_type="text/markdown")
        return Response(content=to_pdf(latest_brief), media_type="application/pdf")
    finally:
        session.close()


@router.get("/prospects/{prospect_id}/briefs")
async def list_brief_versions(
    prospect_id: str, user: AuthenticatedUser = Depends(get_current_user)
) -> list[dict]:
    """List all brief versions for a prospect."""
    session = get_session()
    try:
        repo = ProspectRepository(session)
        briefs = repo.list_brief_versions(prospect_id, owner_id=user.user_id)
        if not briefs:
            raise HTTPException(status_code=404, detail="Prospect not found or no briefs")
        return [
            {"version": b.version, "created_at": b.created_at.isoformat(), "source_run_id": b.source_run_id}
            for b in briefs
        ]
    finally:
        session.close()


@router.get("/prospects/{prospect_id}/briefs/{version}")
async def get_brief_version(
    prospect_id: str, version: int, user: AuthenticatedUser = Depends(get_current_user)
) -> dict:
    """Get a specific brief version."""
    session = get_session()
    try:
        repo = ProspectRepository(session)
        brief = repo.get_brief_version(prospect_id, owner_id=user.user_id, version=version)
        if brief is None:
            raise HTTPException(status_code=404, detail="Brief version not found")
        return brief.data
    finally:
        session.close()


@router.delete("/prospects/{prospect_id}", status_code=204)
async def delete_prospect(
    prospect_id: str, user: AuthenticatedUser = Depends(get_current_user)
) -> None:
    session = get_session()
    try:
        repo = ProspectRepository(session)
        if not repo.delete(prospect_id, owner_id=user.user_id):
            raise HTTPException(status_code=404, detail="Prospect not found")
    finally:
        session.close()
