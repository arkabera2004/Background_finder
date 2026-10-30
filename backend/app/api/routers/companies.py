from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import AuthenticatedUser, get_current_user
from app.db.company_repository import CompanyRepository
from app.db.session import get_session

router = APIRouter()


def _company_to_dict(company) -> dict:
    return {
        "id": company.id,
        "name": company.name,
        "domain": company.domain,
        "data": company.data,
        "crawled_at": company.crawled_at.isoformat() if company.crawled_at else None,
        "created_at": company.created_at.isoformat(),
    }


@router.get("/companies")
async def list_companies(user: AuthenticatedUser = Depends(get_current_user)) -> list[dict]:
    session = get_session()
    try:
        repo = CompanyRepository(session)
        return [_company_to_dict(c) for c in repo.list_for_owner(user.user_id)]
    finally:
        session.close()


@router.get("/companies/{company_id}")
async def get_company(
    company_id: str, user: AuthenticatedUser = Depends(get_current_user)
) -> dict:
    session = get_session()
    try:
        repo = CompanyRepository(session)
        company = repo.get(company_id, owner_id=user.user_id)
        if company is None:
            raise HTTPException(status_code=404, detail="Company not found")
        return _company_to_dict(company)
    finally:
        session.close()


@router.delete("/companies/{company_id}", status_code=204)
async def delete_company(
    company_id: str, user: AuthenticatedUser = Depends(get_current_user)
) -> None:
    session = get_session()
    try:
        repo = CompanyRepository(session)
        if not repo.delete(company_id, owner_id=user.user_id):
            raise HTTPException(status_code=404, detail="Company not found")
    finally:
        session.close()
