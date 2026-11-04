from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.chanakya_models import AgentExecution, Evidence, MonthlyRun, OfferingSnapshot
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

    def mark_run_status(self, run: MonthlyRun, status: RunStatus) -> MonthlyRun:
        run.status = status.value
        if status in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED):
            run.completed_at = datetime.now(timezone.utc)
        self.session.commit()
        return run
