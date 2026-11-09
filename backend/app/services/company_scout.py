"""Agent 02 — Company Scout: discover, score, dedupe, and select companies.

Fit scoring is a crude but honest proxy (fraction of ICP-criteria terms
found in the result's title/snippet) — never a fabricated or inferred
judgement about a company it hasn't actually read anything about.
"""

from app.providers.search_provider import SearchProvider
from app.services.company_discovery import extract_candidate_domain, is_operating_company_page


def score_fit(icp_criteria: list[str], title: str | None, snippet: str | None) -> float:
    if not icp_criteria:
        return 0.0
    text = f"{title or ''} {snippet or ''}".lower()
    hits = sum(1 for c in icp_criteria if c.lower() in text)
    return hits / len(icp_criteria)


async def discover_candidates(
    search: SearchProvider, offerings: list[dict], filters: dict, max_search_results: int = 30
) -> list[dict]:
    """One search per distinct ICP criterion (or a bare industry query if
    none given), deduplicated by domain across all offerings in the brief.
    Returns unpersisted candidate dicts — the caller decides what to keep."""
    icp_criteria = [c for o in offerings for c in o.get("icp_criteria", [])]
    industries = filters.get("industries", [])
    geography = filters.get("geography", [])
    queries = [
        " ".join(part for part in ["companies", *industries, *geography, c] if part) for c in icp_criteria
    ] or [" ".join(part for part in ["companies", *industries, *geography] if part)]

    seen_domains: set[str] = set()
    candidates: list[dict] = []
    failed_queries = 0
    for query in queries:
        try:
            results = await search.search(query, max_results=max_search_results)
        except Exception:  # noqa: BLE001 - one bad query must not sink the whole discovery
            failed_queries += 1
            continue
        for result in results:
            domain = extract_candidate_domain(result.url)
            if not domain or domain in seen_domains:
                continue
            if not is_operating_company_page(result.url, result.title, result.snippet):
                # A media/listicle/directory page about the industry in
                # general, not a specific operating company's own site —
                # confirmed live (run 24882912-...): 48/48 "companies"
                # selected before this check were exactly this.
                continue
            seen_domains.add(domain)
            candidates.append(
                {
                    "name": result.title or domain,
                    "domain": domain,
                    "source_url": result.url,
                    "fit_score": score_fit(icp_criteria, result.title, result.snippet),
                }
            )
    if failed_queries and failed_queries == len(queries):
        raise RuntimeError(f"all {len(queries)} discovery queries failed")
    return candidates


def select_top_companies(candidates: list[dict], target_count: int) -> list[dict]:
    """Highest fit_score first; ties keep discovery order (stable sort)."""
    return sorted(candidates, key=lambda c: c["fit_score"], reverse=True)[:target_count]
