"""Chanakya API: one router module per agent, aggregated here.

Each agent (catalogue, company_scout, people_finder, ...) owns its own
file with its own endpoints and its own provider wiring — nothing here
reaches into another agent's internals, only its persisted output via
app.db.chanakya_repository.
"""

from fastapi import APIRouter

from app.api.routers.chanakya import (
    catalogue,
    company_scout,
    email_hunter,
    linkedin_resolver,
    people_finder,
    profile_researcher,
    qa_sync,
)

router = APIRouter()
router.include_router(catalogue.router)
router.include_router(company_scout.router)
router.include_router(people_finder.router)
router.include_router(linkedin_resolver.router)
router.include_router(email_hunter.router)
router.include_router(profile_researcher.router)
router.include_router(qa_sync.router)
