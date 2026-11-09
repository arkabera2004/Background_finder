"""Identity disambiguation: when a name+company submission could plausibly
match multiple people, search finds candidates and the user must pick one
— never silently guessing among ambiguous matches.

Distinguishing information shown to the user is exactly what the search
provider returned (title/snippet) — never fabricated. If search finds
nothing or a provider isn't configured, it's an empty candidate list, not
an invented one.
"""

from dataclasses import dataclass

from app.providers.search_provider import SearchProvider
from app.services.company_discovery import page_mentions_company


@dataclass
class IdentityCandidate:
    linkedin_url: str
    title: str | None
    snippet: str | None


def _is_linkedin_profile_url(url: str) -> bool:
    return "linkedin.com/in/" in url


async def find_identity_candidates(
    full_name: str, company: str, search: SearchProvider, max_results: int = 5
) -> list[IdentityCandidate]:
    query = f'"{full_name}" "{company}" site:linkedin.com/in'
    results = await search.search(query, max_results=max_results * 2)

    seen_urls: set[str] = set()
    candidates: list[IdentityCandidate] = []
    for r in results:
        if not _is_linkedin_profile_url(r.url) or r.url in seen_urls:
            continue
        # A site:-scoped search still surfaces results that merely mention
        # both names somewhere (e.g. a third party's LinkedIn activity
        # feed reposting something about this person), not a profile that
        # is actually evidence of working at this company. Precision over
        # candidate count: an unrelated namesake's profile that happens
        # not to mention the company at all is noise, not a real
        # candidate — confirmed live on run 24882912-... where exactly
        # this pattern produced unrelated people in otherwise-genuine
        # candidate lists.
        if not page_mentions_company(company, r.title, r.snippet):
            continue
        seen_urls.add(r.url)
        candidates.append(IdentityCandidate(linkedin_url=r.url, title=r.title, snippet=r.snippet))
        if len(candidates) >= max_results:
            break
    return candidates
