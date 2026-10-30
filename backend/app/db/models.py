"""Persistent ORM models.

Key domain decision: a research run and a saved prospect are separate
concepts. Completing a run never auto-creates a Prospect — the user must
explicitly call POST /prospects (see app/api/routers/prospects.py), which
copies the run's resulting brief into a new, independently-owned Prospect
record. This means a user can run throwaway research without cluttering
their library, and a saved Prospect survives even if its originating run
is later deleted/expired.

Uses SQLAlchemy so the same models work against local SQLite (tested here)
and Supabase/Postgres (DATABASE_URL=postgresql://... once provisioned) —
no application code changes needed to switch, only the connection string.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    domain: Mapped[str | None] = mapped_column(String, nullable=True)
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    crawled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    prospects: Mapped[list["Prospect"]] = relationship(back_populates="company")

    __table_args__ = (Index("ix_companies_owner_domain", "owner_id", "domain"),)


class Prospect(Base):
    __tablename__ = "prospects"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    company_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True
    )
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    linkedin_url: Mapped[str | None] = mapped_column(String, nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String, default="new")
    source_run_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    company: Mapped[Company | None] = relationship(back_populates="prospects")
    briefs: Mapped[list["Brief"]] = relationship(back_populates="prospect", cascade="all, delete-orphan")

    __table_args__ = (Index("ix_prospects_owner_created", "owner_id", "created_at"),)


class Brief(Base):
    __tablename__ = "briefs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    prospect_id: Mapped[str] = mapped_column(
        String, ForeignKey("prospects.id", ondelete="CASCADE"), nullable=False
    )
    source_run_id: Mapped[str | None] = mapped_column(String, nullable=True)
    version: Mapped[int] = mapped_column(default=1)
    data: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    prospect: Mapped[Prospect] = relationship(back_populates="briefs")

    __table_args__ = (Index("ix_briefs_prospect_version", "prospect_id", "version"),)
