"""Company domain discovery via search, replacing the guessed-domain heuristic.

Never guesses a domain (e.g. "acme" -> "acme.com") — that fabricates a URL
that may not exist or may belong to an unrelated company. Instead, this
searches for the company's official website and only returns a domain when
the result plausibly matches the company name. `None` means "no confident
match": callers must not fall back to guessing.
"""

import ipaddress
import re
import socket
from urllib.parse import urlparse

from app.providers.search_provider import SearchProvider

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Company-data aggregator/directory sites list thousands of companies, each
# on its own page whose title plausibly contains the target company's name
# — so a naive token match treats them as a strong hit. Crawling one of
# these then pulls in sibling pages for unrelated companies (confirmed
# live: a JoulestoWatts lookup resolved to a LeadIQ listing page and the
# subsequent crawl returned 15 pages for 15 different unrelated companies).
_AGGREGATOR_DOMAINS = {
    "leadiq.com",
    "zoominfo.com",
    "crunchbase.com",
    "owler.com",
    "linkedin.com",
    "bloomberg.com",
    "pitchbook.com",
    "rocketreach.co",
    "apollo.io",
    "dnb.com",
    "glassdoor.com",
    "indeed.com",
    "wikipedia.org",
    "signalhire.com",
    "wellfound.com",
}

# Generic business words that don't distinguish one company from another —
# a match on only these would confidently crawl the wrong company's site.
_GENERIC_TOKENS = {
    "inc",
    "llc",
    "corp",
    "the",
    "company",
    "group",
    "solutions",
    "systems",
    "co",
    "ltd",
    "limited",
    "holdings",
    "international",
    "global",
}


def _tokens(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.lower()))


def page_mentions_company(company_name: str, title: str | None, snippet: str | None) -> bool:
    """Public wrapper for the same distinctive-token check used to pick the
    company's domain — reused by ResearchCompanyStage to filter crawled
    pages (defense in depth: even a domain that passed the aggregator
    blocklist could still be a multi-company directory not on that list;
    a page that never actually mentions the company shouldn't be kept)."""
    return _plausible_match(company_name, title, snippet)


def _plausible_match(company_name: str, title: str | None, snippet: str | None) -> bool:
    company_tokens = _tokens(company_name)
    distinctive_tokens = company_tokens - _GENERIC_TOKENS
    if not distinctive_tokens:
        return False
    candidate_tokens = _tokens(f"{title or ''} {snippet or ''}")
    return bool(distinctive_tokens & candidate_tokens)


def _is_safe_host(hostname: str) -> bool:
    """Reject hosts that resolve to private/loopback/link-local addresses,
    and anything with userinfo-style tricks. Resolution failure is treated
    as unsafe (reject, don't crawl) rather than fail-open."""
    if "@" in hostname:
        return False
    try:
        resolved_ip = socket.gethostbyname(hostname)
        ip = ipaddress.ip_address(resolved_ip)
    except (OSError, ValueError):
        return False
    return not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved)


async def discover_company_domain(search: SearchProvider, company_name: str) -> str | None:
    """Search for `company_name`'s official website and return its
    registered domain, or `None` if no confident match was found."""
    results = await search.search(f'"{company_name}" official website', max_results=10)
    if not results:
        return None

    match = None
    for candidate in results[:5]:
        hostname = urlparse(candidate.url).netloc.lower().removeprefix("www.")
        if any(hostname == d or hostname.endswith(f".{d}") for d in _AGGREGATOR_DOMAINS):
            continue
        if _plausible_match(company_name, candidate.title, candidate.snippet):
            match = candidate
            break
    if match is None:
        return None

    parsed = urlparse(match.url)
    domain = parsed.netloc or parsed.path.split("/")[0]
    if not domain:
        return None
    domain = domain.lower()

    hostname = domain.split(":")[0]
    if "@" in domain or not _is_safe_host(hostname):
        return None

    return domain
