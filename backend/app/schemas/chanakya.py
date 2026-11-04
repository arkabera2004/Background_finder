"""Canonical enums for the Chanakya monthly run lifecycle.

Shared by the ORM models (app/db/chanakya_models.py), the stage runner,
and every agent implementation added in later phases.
"""

from enum import StrEnum


class AgentName(StrEnum):
    CATALOGUE = "catalogue"
    COMPANY_SCOUT = "company_scout"
    PEOPLE_FINDER = "people_finder"
    LINKEDIN_RESOLVER = "linkedin_resolver"
    EMAIL_HUNTER = "email_hunter"
    PROFILE_RESEARCHER = "profile_researcher"
    QA_SYNC = "qa_sync"


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentExecutionStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
