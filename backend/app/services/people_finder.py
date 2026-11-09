"""Agent 03 — People Finder: map leadership roles to candidate leaders per company.

This agent never confirms identity — it only proposes name+role+candidate
LinkedIn-search-result pairs with a plausibility confidence. Agent 04
(LinkedIn Resolver, a later phase) is the one that turns a candidate into
a confirmed profile; nothing here is allowed to claim `identity_confirmed`.
"""

import re

from app.providers.search_provider import SearchProvider

PRIORITY_ROLES = [
    "CEO",
    "CTO",
    "CIO",
    "CDO",
    "VP Engineering",
    "VP Product",
    "COO",
    "Head of AI",
]

_LINKEDIN_TITLE_RE = re.compile(r"^(?P<name>[A-Z][\w.'-]+(?:\s+[A-Z][\w.'-]+){1,3})\s*[-–]\s*\S")

# Whole-word organisation/role-entity indicators — a "name" containing one
# of these is an organisation, product, or generic label, not a person,
# even when it happens to pass the capitalized-words-then-dash title shape
# (e.g. "CIO Connect — CIO", "Kafum Engineering — VP Engineering", both
# found as false positives in run 24882912-...).
_ORGANISATION_WORDS = {
    "connect", "labs", "systems", "engineering", "operating", "energy",
    "database", "collective", "learning", "materials", "material",
    "ventures", "capital", "partners", "group", "network", "institute",
}


def is_linkedin_profile_url(url: str) -> bool:
    """A real personal LinkedIn profile, not a company page, a post, or
    an unrelated third-party site a search engine happened to surface."""
    return "linkedin.com/in/" in url


def _looks_like_an_organisation(name: str) -> bool:
    tokens = {t.lower() for t in name.replace("'s", "").split()}
    return bool(tokens & _ORGANISATION_WORDS)


def extract_name_from_result_title(title: str | None) -> str | None:
    """LinkedIn search results title as "First Last - Role - Company | LinkedIn".
    Returns the leading name segment, or None if it doesn't look like one —
    never guesses a name that isn't actually present in the text."""
    if not title:
        return None
    match = _LINKEDIN_TITLE_RE.match(title.strip())
    return match.group("name").strip() if match else None


def _normalize_name(name: str) -> str:
    return " ".join(name.lower().split())


def score_confidence(url: str, title: str | None, company_name: str, role: str) -> float:
    confidence = 0.0
    if "linkedin.com/in/" in url:
        confidence += 0.6
    text = (title or "").lower()
    if any(tok in text for tok in company_name.lower().split() if len(tok) > 2):
        confidence += 0.2
    if role.lower() in text:
        confidence += 0.2
    return min(confidence, 1.0)


async def discover_people_for_company(
    search: SearchProvider,
    company_name: str,
    roles: list[str] | None = None,
    max_per_role: int = 3,
) -> list[dict]:
    """One search per priority role, deduplicated by normalized name
    (the same person showing up for two role queries keeps only the
    higher-confidence/first-seen candidate)."""
    roles = roles or PRIORITY_ROLES
    seen: dict[str, dict] = {}
    for role in roles:
        query = f'"{company_name}" {role} linkedin'
        for result in await search.search(query, max_results=max_per_role):
            if not is_linkedin_profile_url(result.url):
                # Not a personal profile at all — a company directory page
                # (tracxn.com, zoominfo.com), a LinkedIn *post* rather than
                # a profile, an investor-tracking site, etc. Confirmed live
                # (run 24882912-...): every single false "person" found in
                # production (an organisation name, a post title, an
                # article) had a non-profile URL; every genuine person had
                # a real linkedin.com/in/ URL. Reject outright rather than
                # scoring it low — a non-profile URL is not weak evidence
                # of a person, it is proof this result isn't a person.
                continue
            name = extract_name_from_result_title(result.title)
            if not name or _looks_like_an_organisation(name):
                continue
            key = _normalize_name(name)
            if key in seen:
                continue
            seen[key] = {
                "full_name": name,
                "role": role,
                "linkedin_url": result.url,
                "confidence": score_confidence(result.url, result.title, company_name, role),
                "identity_confirmed": False,
            }
    return list(seen.values())


def select_leaders(candidates: list[dict], target_count: int) -> list[dict]:
    """Highest-confidence first, capped at target_count."""
    return sorted(candidates, key=lambda c: c["confidence"], reverse=True)[:target_count]
