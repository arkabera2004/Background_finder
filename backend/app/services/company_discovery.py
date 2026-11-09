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
    "tracxn.com",
    "craft.co",
    "ensun.io",
    "globaldatabase.com",
}

# Media/publisher/listicle/glossary sites: these run entire sections of
# "Top N fintech companies" or "what is Series B" content, and a bare
# keyword search ("companies fintech Series B") ranks that content highly
# — but a listicle *about* an industry is not itself an operating company.
# Confirmed live (run 24882912-...): every one of 48 "companies" company
# scout selected was a page on one of these domains, zero were an actual
# company's own homepage.
_MEDIA_AND_LISTICLE_DOMAINS = {
    "builtin.com", "builtinnyc.com", "forbes.com", "techcrunch.com",
    "businessinsider.com", "medium.com", "reddit.com", "quora.com",
    "hubspot.com", "ibm.com", "investmentnews.com", "itchronicles.com",
    "startupsavant.com", "techslang.com", "topstartups.io", "vault.com",
    "wallstreetmojo.com", "work-schedule.net", "pilot.com", "plaid.com",
    "startups.gallery", "vcbacked.co", "aletheiaai.in", "datocapital.uk",
    "dearstage2.com", "employbl.com", "engineerbabu.com",
    "entrepreneurscollective.biz", "finance.yahoo.com",
    "find-and-update.company-information.service.gov.uk", "fintechly.com",
    "fundraiseinsider.com", "imarticus.org", "johngauch.com",
    "lowercarbon.com", "pipelineroad.com", "projectstartups.com",
    "protecrea.org", "purpose.jobs", "recentfunding.com", "refolk.ai",
    "seedtable.com", "startups.com", "uk.globaldatabase.com",
    "origami.chat", "ccstartup.com",
}

# A real operating company's own homepage/about page has a shallow URL
# path. A listicle, blog post, glossary entry, or directory search result
# almost always lives several segments deep, or carries query params for
# pagination/filtering (?page=2). This catches listicle pages on domains
# not already in the blocklist above (the blocklist can't be exhaustive).
_NON_HOMEPAGE_PATH_RE = re.compile(
    r"/(blog|articles?|news|glossary|guide|search|companies|startups|posts?)(/|$|\?)", re.I
)

# Headline/listicle phrasing — a page *about* a market segment, not a
# specific company's own site, even when the URL path looks shallow.
_LISTICLE_TITLE_RE = re.compile(
    r"\b(top \d|top\s+\w+\s+fintech|best\s|\d+\s+(fintech|startups?|companies)|"
    r"what is|guide to|definition|vs\.?\s|list of|companies in|startups in)\b",
    re.I,
)

# A venture capital / investment firm is not an operating company and is
# not itself a Series B-funded startup, even when its own site passes
# every other check (confirmed live: fintech.io, "FinTech Collective",
# an investor — not a portfolio company — slipped through as a
# "qualified" Series B fintech company).
_VC_FIRM_RE = re.compile(
    r"\b(venture capital|venture partners|early[- ]stage investor|"
    r"invests? in startups|our portfolio compan)\b",
    re.I,
)


def is_operating_company_page(url: str, title: str | None, snippet: str | None = None) -> bool:
    """True only for a page that plausibly IS a specific operating
    company's own site — not an article, directory, glossary, VC firm,
    or listing about companies in general. Deterministic and
    conservative: when in doubt, reject rather than let an unverified
    page through as a "qualified" company."""
    parsed = urlparse(url)
    hostname = parsed.netloc.lower().removeprefix("www.")
    if any(hostname == d or hostname.endswith(f".{d}") for d in _MEDIA_AND_LISTICLE_DOMAINS):
        return False
    if parsed.query or _NON_HOMEPAGE_PATH_RE.search(parsed.path):
        return False
    text = f"{title or ''} {snippet or ''}"
    if title and _LISTICLE_TITLE_RE.search(title):
        return False
    if _VC_FIRM_RE.search(text):
        return False
    return True

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


def extract_candidate_domain(url: str) -> str | None:
    """Normalize a search-result URL to a safe, non-aggregator domain, or
    `None`. Shared by `discover_company_domain` (resolving one already-named
    company) and the Company Scout agent (turning raw search results into
    candidate companies) — same safety rules, same aggregator blocklist."""
    hostname = urlparse(url).netloc.lower().removeprefix("www.")
    if not hostname:
        return None
    if any(hostname == d or hostname.endswith(f".{d}") for d in _AGGREGATOR_DOMAINS):
        return None
    if "@" in hostname or not _is_safe_host(hostname.split(":")[0]):
        return None
    return hostname


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
