from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db.chanakya_models import (
    AgentExecution,
    EmailCandidate,
    Evidence,
    MonthlyRun,
    OfferingSnapshot,
    Person,
    QARecord,
    ResearchBrief,
    ScoutedCompany,
)
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

    def count_recent_runs_for_owner(self, owner_id: str, since: datetime) -> int:
        return (
            self.session.query(MonthlyRun)
            .filter(MonthlyRun.owner_id == owner_id, MonthlyRun.created_at >= since)
            .count()
        )

    def purge_expired_runs(self, days: int) -> int:
        """Deletes MonthlyRuns (and, via cascade, every stage/company/person/
        email/brief/QA record under them) older than `days`. Mirrors
        ProspectLens's purge_expired_runs for the single-prospect Run —
        same retention policy, applied to the Chanakya schema."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        expired = self.session.query(MonthlyRun).filter(MonthlyRun.created_at < cutoff).all()
        count = len(expired)
        for run in expired:
            self.session.delete(run)
        self.session.commit()
        return count

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

    def upsert_email_candidates(
        self, run_id: str, owner_id: str, person_id: str, candidates: list[dict]
    ) -> list[EmailCandidate]:
        """Dedup by (run_id, person_id, email): re-running the hunt for a
        person updates an existing candidate's verification rather than
        duplicating it."""
        existing = {
            c.email: c
            for c in self.session.query(EmailCandidate)
            .filter(EmailCandidate.run_id == run_id, EmailCandidate.person_id == person_id)
            .all()
        }
        result: list[EmailCandidate] = []
        for candidate in candidates:
            email = candidate["email"]
            if email in existing:
                row = existing[email]
                row.verification_status = candidate["verification_status"]
                row.confidence = candidate["confidence"]
            else:
                row = EmailCandidate(
                    owner_id=owner_id,
                    run_id=run_id,
                    person_id=person_id,
                    email=email,
                    pattern=candidate["pattern"],
                    verification_status=candidate["verification_status"],
                    confidence=candidate["confidence"],
                )
                self.session.add(row)
                existing[email] = row
            result.append(row)
        self.session.commit()
        return result

    def list_email_candidates(self, run_id: str, person_id: str | None = None) -> list[EmailCandidate]:
        query = self.session.query(EmailCandidate).filter(EmailCandidate.run_id == run_id)
        if person_id:
            query = query.filter(EmailCandidate.person_id == person_id)
        return query.order_by(EmailCandidate.confidence.desc()).all()

    def upsert_research_brief(
        self, run_id: str, owner_id: str, person_id: str, status: str, data: dict
    ) -> ResearchBrief:
        """Dedup by (run_id, person_id): re-running research for a person
        replaces the prior brief rather than accumulating duplicates."""
        existing = (
            self.session.query(ResearchBrief)
            .filter(ResearchBrief.run_id == run_id, ResearchBrief.person_id == person_id)
            .one_or_none()
        )
        if existing:
            existing.status = status
            existing.data = data
            self.session.commit()
            return existing

        brief = ResearchBrief(
            owner_id=owner_id, run_id=run_id, person_id=person_id, status=status, data=data
        )
        self.session.add(brief)
        self.session.commit()
        return brief

    def list_research_briefs(self, run_id: str, person_id: str | None = None) -> list[ResearchBrief]:
        query = self.session.query(ResearchBrief).filter(ResearchBrief.run_id == run_id)
        if person_id:
            query = query.filter(ResearchBrief.person_id == person_id)
        return query.order_by(ResearchBrief.created_at.desc()).all()

    def upsert_qa_record(
        self,
        run_id: str,
        owner_id: str,
        person_id: str,
        confidence_score: float,
        confidence_level: str,
        needs_review: bool,
        draft_subject: str,
        draft_body: str,
    ) -> QARecord:
        """Dedup by (run_id, person_id): re-running QA replaces the score
        and draft but never resets an existing human approval decision."""
        existing = (
            self.session.query(QARecord)
            .filter(QARecord.run_id == run_id, QARecord.person_id == person_id)
            .one_or_none()
        )
        if existing:
            existing.confidence_score = confidence_score
            existing.confidence_level = confidence_level
            existing.needs_review = needs_review
            existing.draft_subject = draft_subject
            existing.draft_body = draft_body
            self.session.commit()
            return existing

        record = QARecord(
            owner_id=owner_id,
            run_id=run_id,
            person_id=person_id,
            confidence_score=confidence_score,
            confidence_level=confidence_level,
            needs_review=needs_review,
            draft_subject=draft_subject,
            draft_body=draft_body,
        )
        self.session.add(record)
        self.session.commit()
        return record

    def list_qa_records(self, run_id: str, needs_review_only: bool = False) -> list[QARecord]:
        query = self.session.query(QARecord).filter(QARecord.run_id == run_id)
        if needs_review_only:
            query = query.filter(QARecord.needs_review.is_(True))
        return query.order_by(QARecord.confidence_score.desc()).all()

    def get_qa_record(self, run_id: str, person_id: str) -> QARecord | None:
        return (
            self.session.query(QARecord)
            .filter(QARecord.run_id == run_id, QARecord.person_id == person_id)
            .one_or_none()
        )

    def set_qa_approval(self, record: QARecord, approved: bool) -> QARecord:
        record.approval_status = "approved" if approved else "rejected"
        self.session.commit()
        return record

    def mark_run_status(self, run: MonthlyRun, status: RunStatus) -> MonthlyRun:
        run.status = status.value
        if status in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED):
            run.completed_at = datetime.now(timezone.utc)
        self.session.commit()
        return run
