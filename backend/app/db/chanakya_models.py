"""Chanakya monthly-run domain foundation.

Separate module from app/db/models.py (ProspectLens's single-prospect
schema) since Chanakya is an additive product, not a replacement — see
docs/CHANAKYA_GAP_ANALYSIS.md. Shares the same declarative `Base` and
engine/session so both schemas live in one database.

Lifecycle: a MonthlyRun owns one versioned OfferingSnapshot (Agent 01's
output — reproducible, never mutated after creation) and a sequence of
AgentExecution rows, one per agent per run, tracking status/retries/errors
so the pipeline is resumable without duplicating work (re-running a stage
whose AgentExecution is already COMPLETED is a no-op at the orchestration
layer added in Phase 9). Evidence is the generic provenance record every
later agent (company scout, people finder, resolver, email hunter,
profile researcher) attaches facts to, so "where did this come from" is
answerable without each agent inventing its own sourcing table.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models import Base
from app.schemas.chanakya import AgentExecutionStatus, RunStatus


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class MonthlyRun(Base):
    __tablename__ = "chanakya_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    period: Mapped[str] = mapped_column(String, nullable=False)  # "2026-11"
    status: Mapped[str] = mapped_column(String, default=RunStatus.PENDING, nullable=False)
    config: Mapped[dict] = mapped_column(JSON, default=dict)  # target counts, limits, provider choices
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    offering_snapshots: Mapped[list["OfferingSnapshot"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    agent_executions: Mapped[list["AgentExecution"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    evidence: Mapped[list["Evidence"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    scouted_companies: Mapped[list["ScoutedCompany"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    people: Mapped[list["Person"]] = relationship(back_populates="run", cascade="all, delete-orphan")

    __table_args__ = (Index("ix_chanakya_runs_owner_period", "owner_id", "period"),)


class OfferingSnapshot(Base):
    """Agent 01's versioned output: the ICP/offering brief a run was executed against.

    Never mutated after creation — editing offerings creates a new version,
    so a completed run always points at the exact brief it used.
    """

    __tablename__ = "chanakya_offering_snapshots"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    run_id: Mapped[str] = mapped_column(
        String, ForeignKey("chanakya_runs.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    data: Mapped[dict] = mapped_column(JSON, nullable=False)  # offerings, ICP criteria, filters
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    run: Mapped[MonthlyRun] = relationship(back_populates="offering_snapshots")

    __table_args__ = (Index("ix_offering_snapshots_run_version", "run_id", "version"),)


class AgentExecution(Base):
    """One row per agent per run — status, retries, errors, provenance."""

    __tablename__ = "chanakya_agent_executions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(
        String, ForeignKey("chanakya_runs.id", ondelete="CASCADE"), nullable=False
    )
    agent_name: Mapped[str] = mapped_column(String, nullable=False)  # AgentName value
    status: Mapped[str] = mapped_column(String, default=AgentExecutionStatus.PENDING, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_summary: Mapped[dict] = mapped_column(JSON, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    run: Mapped[MonthlyRun] = relationship(back_populates="agent_executions")

    __table_args__ = (
        Index("ix_agent_executions_run_agent", "run_id", "agent_name", unique=True),
    )


class Evidence(Base):
    """Generic provenance record: which source backs which fact about which entity.

    entity_type/entity_id are a loose reference (not a FK) since the
    entities themselves — companies, people, emails, briefs — are
    introduced by later phases per agent; this table exists first so
    every agent from Phase 3 onward has somewhere to record sourcing
    from day one instead of retrofitting it.
    """

    __tablename__ = "chanakya_evidence"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(
        String, ForeignKey("chanakya_runs.id", ondelete="CASCADE"), nullable=False
    )
    agent_name: Mapped[str] = mapped_column(String, nullable=False)
    entity_type: Mapped[str] = mapped_column(String, nullable=False)  # "company" | "person" | "email" | ...
    entity_id: Mapped[str] = mapped_column(String, nullable=False)
    source_url: Mapped[str] = mapped_column(String, nullable=False)
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(default=0.0, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    run: Mapped[MonthlyRun] = relationship(back_populates="evidence")

    __table_args__ = (Index("ix_evidence_entity", "entity_type", "entity_id"),)


class ScoutedCompany(Base):
    """Agent 02's output: a company discovered for a run, scored for ICP
    fit, and optionally selected into the run's final top-N set."""

    __tablename__ = "chanakya_scouted_companies"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    run_id: Mapped[str] = mapped_column(
        String, ForeignKey("chanakya_runs.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    domain: Mapped[str] = mapped_column(String, nullable=False)
    fit_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    selected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source_url: Mapped[str] = mapped_column(String, nullable=False)
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    run: Mapped[MonthlyRun] = relationship(back_populates="scouted_companies")

    __table_args__ = (Index("ix_scouted_companies_run_domain", "run_id", "domain", unique=True),)


class Person(Base):
    """Agent 03's output: a candidate leader proposed for a company and
    role. `identity_confirmed` stays False here always — only Agent 04
    (LinkedIn Resolver) is allowed to flip it, after real disambiguation."""

    __tablename__ = "chanakya_people"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    run_id: Mapped[str] = mapped_column(
        String, ForeignKey("chanakya_runs.id", ondelete="CASCADE"), nullable=False
    )
    company_id: Mapped[str] = mapped_column(
        String, ForeignKey("chanakya_scouted_companies.id", ondelete="CASCADE"), nullable=False
    )
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    linkedin_url: Mapped[str | None] = mapped_column(String, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    identity_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    run: Mapped[MonthlyRun] = relationship(back_populates="people")
    company: Mapped[ScoutedCompany] = relationship()

    __table_args__ = (
        Index("ix_people_run_company_name", "run_id", "company_id", "full_name", unique=True),
    )
