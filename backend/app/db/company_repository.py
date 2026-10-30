from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.db.models import Company


class CompanyRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_or_create(self, owner_id: str, name: str, domain: str | None) -> Company:
        """Get existing company by domain (if provided) or create a new one.
        This is the path from research_company stage — exact company matching."""
        if domain:
            existing = (
                self.session.query(Company)
                .filter(Company.owner_id == owner_id, Company.domain == domain)
                .one_or_none()
            )
            if existing:
                return existing

        company = Company(owner_id=owner_id, name=name, domain=domain)
        self.session.add(company)
        self.session.flush()
        return company

    def get(self, company_id: str, owner_id: str) -> Company | None:
        return (
            self.session.query(Company)
            .filter(Company.id == company_id, Company.owner_id == owner_id)
            .one_or_none()
        )

    def list_for_owner(self, owner_id: str) -> list[Company]:
        return (
            self.session.query(Company)
            .filter(Company.owner_id == owner_id)
            .order_by(Company.created_at.desc())
            .all()
        )

    def delete(self, company_id: str, owner_id: str) -> bool:
        company = self.get(company_id, owner_id)
        if company is None:
            return False
        self.session.delete(company)
        self.session.commit()
        return True

    def update_research_data(self, company_id: str, owner_id: str, data: dict) -> Company | None:
        company = self.get(company_id, owner_id)
        if company is None:
            return None
        company.data.update(data)
        flag_modified(company, "data")
        self.session.commit()
        return company
