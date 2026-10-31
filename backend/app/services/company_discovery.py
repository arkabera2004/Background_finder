"""Company domain discovery via search, replacing the guessed-domain heuristic.

Never guesses a domain (e.g. "acme" -> "acme.com") — that fabricates a URL
that may not exist or may belong to an unrelated company. Instead, this
searches for the company's official website and only returns a domain when
the result plausibly matches the company name. `None` means "no confident
match": callers must not fall back to guessing.
"""

import re
from urllib.parse import urlparse

from app.providers.search_provider import SearchProvider

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.lower()))


def _plausible_match(company_name: str, title: str | None, snippet: str | None) -> bool:
    company_tokens = _tokens(company_name)
    if not company_tokens:
        return False
    candidate_tokens = _tokens(f"{title or ''} {snippet or ''}")
    return bool(company_tokens & candidate_tokens)


async def discover_company_domain(search: SearchProvider, company_name: str) -> str | None:
    """Search for `company_name`'s official website and return its
    registered domain, or `None` if no confident match was found."""
    results = await search.search(f'"{company_name}" official website', max_results=10)
    if not results:
        return None

    first = results[0]
    if not _plausible_match(company_name, first.title, first.snippet):
        return None

    parsed = urlparse(first.url)
    domain = parsed.netloc or parsed.path.split("/")[0]
    if not domain:
        return None
    return domain.lower()
