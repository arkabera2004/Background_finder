from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.chanakya_models import AgentExecution, Evidence, MonthlyRun, OfferingSnapshot, Person, ScoutedCompany
from app.schemas.chanakya import AgentExecutionStatus, AgentName, RunStatus


class ChanakyaRunRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_run(self, owner_id: str, period: str, config: dict | None = None) -> MonthlyRun:
        run = MonthlyRun(owner_id=owner_id, period=period, config=config or {})
        self.session.add(run)
        self.session.flush()
        for agent in AgentName:
            self.session.add(AgentExecution(run_id=run.id, agent_name=agent.value))
        self.session.commit()
        return run

    def get(self, run_id: str, owner_id: str) -> MonthlyRun | None:
        return (
            self.session.query(MonthlyRun)
            .filter(MonthlyRun.id == run_id, MonthlyRun.owner_id == owner_id)
            .one_or_none()
        )

    def list_for_owner(self, owner_id: str) -> list[MonthlyRun]:
        return (
            self.session.query(MonthlyRun)
            .filter(MonthlyRun.owner_id == owner_id)
            .order_by(MonthlyRun.created_at.desc())
            .all()
        )

    def add_offering_snapshot(self, run: MonthlyRun, data: dict) -> OfferingSnapshot:
        """Versioned and append-only: editing offerings never mutates a prior snapshot."""
        max_version = max((s.version for s in run.offering_snapshots), default=0)
        snapshot = OfferingSnapshot(
            owner_id=run.owner_id, run_id=run.id, version=max_version + 1, data=data
        )
        self.session.add(snapshot)
        self.session.commit()
        return snapshot

    def _get_execution(self, run_id: str, agent_name: AgentName) -> AgentExecution:
        execution = (
            self.session.query(AgentExecution)
            .filter(AgentExecution.run_id == run_id, AgentExecution.agent_name == agent_name.value)
            .one_or_none()
        )
        if execution is None:
            raise ValueError(f"No AgentExecution row for {agent_name} on run {run_id}")
        return execution

    def start_agent(self, run_id: str, agent_name: AgentName) -> AgentExecution:
        """Idempotent: calling this on an already-COMPLETED agent is a no-op that
        returns the existing record, so a resumed run never redoes finished work."""
        execution = self._get_execution(run_id, agent_name)
        if execution.status == AgentExecutionStatus.COMPLETED:
            return execution
        execution.status = AgentExecutionStatus.RUNNING
        execution.started_at = datetime.now(timezone.utc)
        self.session.commit()
        return execution

    def complete_agent(self, run_id: str, agent_name: AgentName, output_summary: dict | None = None) -> AgentExecution:
        execution = self._get_execution(run_id, agent_name)
        execution.status = AgentExecutionStatus.COMPLETED
        execution.output_summary = output_summary or {}
        execution.error = None
        execution.completed_at = datetime.now(timezone.utc)
        self.session.commit()
        return execution

    def fail_agent(self, run_id: str, agent_name: AgentName, error: str) -> AgentExecution:
        execution = self._get_execution(run_id, agent_name)
        execution.status = AgentExecutionStatus.FAILED
        execution.retry_count += 1
        execution.error = error
        self.session.commit()
        return execution

    def add_evidence(
        self,
        run_id: str,
        agent_name: AgentName,
        entity_type: str,
        entity_id: str,
        source_url: str,
        confidence: float,
        excerpt: str | None = None,
    ) -> Evidence:
        evidence = Evidence(
            run_id=run_id,
            agent_name=agent_name.value,
            entity_type=entity_type,
            entity_id=entity_id,
            source_url=source_url,
            confidence=confidence,
            excerpt=excerpt,
        )
        self.session.add(evidence)
        self.session.commit()
        return evidence

    def upsert_scouted_companies(self, run_id: str, owner_id: str, candidates: list[dict]) -> list[ScoutedCompany]:
        """Dedup by (run_id, domain): re-running discovery on the same run
        updates an existing candidate's score/source rather than duplicating it."""
        existing = {
            c.domain: c
            for c in self.session.query(ScoutedCompany).filter(ScoutedCompany.run_id == run_id).all()
        }
        result: list[ScoutedCompany] = []
        for candidate in candidates:
            domain = candidate["domain"]
            if domain in existing:
                row = existing[domain]
                row.name = candidate["name"]
                row.fit_score = candidate["fit_score"]
                row.source_url = candidate["source_url"]
            else:
                row = ScoutedCompany(
                    owner_id=owner_id,
                    run_id=run_id,
                    name=candidate["name"],
                    domain=domain,
                    fit_score=candidate["fit_score"],
                    source_url=candidate["source_url"],
                )
                self.session.add(row)
                existing[domain] = row
            result.append(row)
        self.session.commit()
        return result

    def select_top_companies(self, run_id: str, target_count: int) -> list[ScoutedCompany]:
        """Marks the highest-fit_score `target_count` companies `selected`
        and clears the flag on everyone else, so re-running selection with a
        different target is idempotent rather than additive."""
        companies = (
            self.session.query(ScoutedCompany).filter(ScoutedCompany.run_id == run_id).all()
        )
        ranked = sorted(companies, key=lambda c: c.fit_score, reverse=True)
        selected_ids = {c.id for c in ranked[:target_count]}
        for company in companies:
            company.selected = company.id in selected_ids
        self.session.commit()
        return [c for c in ranked if c.id in selected_ids]

    def list_scouted_companies(self, run_id: str, selected_only: bool = False) -> list[ScoutedCompany]:
        query = self.session.query(ScoutedCompany).filter(ScoutedCompany.run_id == run_id)
        if selected_only:
            query = query.filter(ScoutedCompany.selected.is_(True))
        return query.order_by(ScoutedCompany.fit_score.desc()).all()

    def upsert_people(self, run_id: str, owner_id: str, company_id: str, candidates: list[dict]) -> list[Person]:
        """Dedup by (run_id, company_id, full_name): re-running discovery
        for a company updates an existing candidate's role/confidence
        rather than duplicating them."""
        existing = {
            p.full_name: p
            for p in self.session.query(Person)
            .filter(Person.run_id == run_id, Person.company_id == company_id)
            .all()
        }
        result: list[Person] = []
        for candidate in candidates:
            name = candidate["full_name"]
            if name in existing:
                row = existing[name]
                row.role = candidate["role"]
                row.linkedin_url = candidate["linkedin_url"]
                row.confidence = candidate["confidence"]
            else:
                row = Person(
                    owner_id=owner_id,
                    run_id=run_id,
                    company_id=company_id,
                    full_name=name,
                    role=candidate["role"],
                    linkedin_url=candidate["linkedin_url"],
                    confidence=candidate["confidence"],
                )
                self.session.add(row)
                existing[name] = row
            result.append(row)
        self.session.commit()
        return result

    def list_people(self, run_id: str, company_id: str | None = None) -> list[Person]:
        query = self.session.query(Person).filter(Person.run_id == run_id)
        if company_id:
            query = query.filter(Person.company_id == company_id)
        return query.order_by(Person.confidence.desc()).all()

    def get_person(self, person_id: str, run_id: str) -> Person | None:
        return (
            self.session.query(Person)
            .filter(Person.id == person_id, Person.run_id == run_id)
            .one_or_none()
        )

    def apply_resolution(
        self, person: Person, resolution_status: str, linkedin_url: str | None, candidate_profiles: list
    ) -> Person:
        person.resolution_status = resolution_status
        person.candidate_profiles = candidate_profiles
        if resolution_status == "confirmed":
            person.linkedin_url = linkedin_url
            person.identity_confirmed = True
        self.session.commit()
        return person

    def confirm_person_manually(self, person: Person, linkedin_url: str) -> Person:
        """A human picked one of the ambiguous candidates (or supplied a
        fresh URL) — the manual-review-queue resolution path."""
        person.linkedin_url = linkedin_url
        person.identity_confirmed = True
        person.resolution_status = "confirmed"
        self.session.commit()
        return person

    def mark_run_status(self, run: MonthlyRun, status: RunStatus) -> MonthlyRun:
        run.status = status.value
        if status in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED):
            run.completed_at = datetime.now(timezone.utc)
        self.session.commit()
        return run
