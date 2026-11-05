import pytest

from app.providers.search_provider import SearchProvider, SearchResult
from app.services.company_scout import discover_candidates, score_fit, select_top_companies


class FakeSearchProvider(SearchProvider):
    name = "fake"

    def __init__(self, results_by_query: dict[str, list[SearchResult]]):
        self._results_by_query = results_by_query

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        return self._results_by_query.get(query, [])


def test_score_fit_counts_matched_criteria():
    assert score_fit(["fintech", "Series B"], "Acme is a fintech company", None) == 0.5
    assert score_fit(["fintech", "Series B"], "Acme is a fintech company, Series B funded", None) == 1.0
    assert score_fit([], "anything", None) == 0.0


@pytest.mark.asyncio
async def test_discover_candidates_dedupes_by_domain_and_filters_aggregators(monkeypatch):
    from app.services import company_discovery

    monkeypatch.setattr(company_discovery, "_is_safe_host", lambda hostname: True)

    results = {
        "companies fintech": [
            SearchResult(url="https://acme.com/about", title="Acme fintech Series B", snippet="..."),
            SearchResult(url="https://acme.com/careers", title="Acme careers", snippet="..."),  # dup domain
            SearchResult(url="https://crunchbase.com/acme", title="Acme on Crunchbase", snippet="..."),
        ]
    }
    search = FakeSearchProvider(results)

    candidates = await discover_candidates(
        search,
        offerings=[{"icp_criteria": ["fintech"]}],
        filters={"industries": []},
    )

    assert len(candidates) == 1
    assert candidates[0]["domain"] == "acme.com"
    assert candidates[0]["fit_score"] == 1.0


def test_select_top_companies_ranks_by_fit_score():
    candidates = [
        {"name": "A", "domain": "a.com", "source_url": "https://a.com", "fit_score": 0.2},
        {"name": "B", "domain": "b.com", "source_url": "https://b.com", "fit_score": 0.9},
        {"name": "C", "domain": "c.com", "source_url": "https://c.com", "fit_score": 0.5},
    ]

    top_two = select_top_companies(candidates, 2)

    assert [c["domain"] for c in top_two] == ["b.com", "c.com"]
