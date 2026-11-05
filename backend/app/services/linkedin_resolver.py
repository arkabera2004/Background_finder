"""Agent 04 — LinkedIn Resolver: confirm (or queue for human review) the
identity of a candidate leader proposed by Agent 03 (People Finder).

Reuses `find_identity_candidates` (the same search-based disambiguation
already proven in ProspectLens's single-prospect identity resolution) —
no separate Clay/browser waterfall tiers exist yet; those are documented
as the next waterfall steps in docs/PROVIDER_INTEGRATIONS.md and slot in
ahead of search without changing this function's contract. Exactly one
candidate is the only case this agent confirms automatically; zero or
multiple candidates always go to the manual review queue rather than
guessing.
"""

from dataclasses import asdict

from app.providers.search_provider import SearchProvider
from app.services.identity_resolution import find_identity_candidates


async def resolve_person_identity(search: SearchProvider, full_name: str, company_name: str) -> dict:
    candidates = await find_identity_candidates(full_name, company_name, search)
    candidate_dicts = [asdict(c) for c in candidates]

    if len(candidates) == 0:
        return {"resolution_status": "unresolved", "linkedin_url": None, "candidate_profiles": []}
    if len(candidates) == 1:
        return {
            "resolution_status": "confirmed",
            "linkedin_url": candidates[0].linkedin_url,
            "candidate_profiles": candidate_dicts,
        }
    return {"resolution_status": "ambiguous", "linkedin_url": None, "candidate_profiles": candidate_dicts}
