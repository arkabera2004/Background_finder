from sqlalchemy.orm import Session

from app.db.models import Brief, Prospect


class ProspectRepository:
    def __init__(self, session: Session):
        self.session = session

    def save_from_run(
        self, owner_id: str, full_name: str, linkedin_url: str | None, run_id: str, brief_data: dict
    ) -> Prospect:
        """Explicitly promote a completed run's result into a saved Prospect.
        Never called automatically — see app/db/models.py module docstring."""
        prospect = Prospect(
            owner_id=owner_id,
            full_name=full_name,
            linkedin_url=linkedin_url,
            source_run_id=run_id,
        )
        self.session.add(prospect)
        self.session.flush()  # assigns prospect.id

        brief = Brief(
            owner_id=owner_id,
            prospect_id=prospect.id,
            source_run_id=run_id,
            version=1,
            data=brief_data,
        )
        self.session.add(brief)
        self.session.commit()
        return prospect

    def get(self, prospect_id: str, owner_id: str) -> Prospect | None:
        return (
            self.session.query(Prospect)
            .filter(Prospect.id == prospect_id, Prospect.owner_id == owner_id)
            .one_or_none()
        )

    def list_for_owner(self, owner_id: str) -> list[Prospect]:
        return (
            self.session.query(Prospect)
            .filter(Prospect.owner_id == owner_id)
            .order_by(Prospect.created_at.desc())
            .all()
        )

    def delete(self, prospect_id: str, owner_id: str) -> bool:
        prospect = self.get(prospect_id, owner_id)
        if prospect is None:
            return False
        self.session.delete(prospect)
        self.session.commit()
        return True
