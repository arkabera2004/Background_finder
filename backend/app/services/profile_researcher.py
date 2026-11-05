"""Agent 06 — Profile Researcher: produce a source-backed brief per leader.

Deliberately does not reimplement career/activity/company research — that
already exists, tested, as ProspectLens's single-prospect pipeline
(ResolveIdentityStage -> ... -> SynthesiseBriefStage, with the existing
citation validator dropping any fabricated source). This agent is a thin
driver: for a confirmed person with a linkedin_url, run that exact
pipeline and hand back its brief, honestly reporting when a run didn't
complete rather than inventing a brief.
"""

from app.services.research_service import create_run, execute_run


async def research_person(owner_id: str, full_name: str, linkedin_url: str, company_name: str) -> dict:
    run = create_run(
        owner_id=owner_id,
        depth="standard",
        full_name=full_name,
        linkedin_url=linkedin_url,
        company=company_name,
        pasted_text=None,
    )
    await execute_run(run)
    return {"status": run.status, "brief": run.brief}
