import pytest

from app.providers.search_provider import SearchProvider, SearchResult
from app.services.company_discovery import discover_company_domain


class FakeSearchProvider(SearchProvider):
    name = "fake"

    def __init__(self, results: list[SearchResult]):
        self._results = results

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        return self._results


@pytest.mark.asyncio
async def test_discover_company_domain_returns_domain_on_confident_match():
    search = FakeSearchProvider(
        [
            SearchResult(
                url="https://acmerobotics.com/about",
                title="Acme Robotics - Official Website",
                snippet="Acme Robotics builds industrial robots.",
            )
        ]
    )

    domain = await discover_company_domain(search, "Acme Robotics")

    assert domain == "acmerobotics.com"


@pytest.mark.asyncio
async def test_discover_company_domain_returns_none_on_zero_results():
    search = FakeSearchProvider([])

    domain = await discover_company_domain(search, "Acme Robotics")

    assert domain is None


@pytest.mark.asyncio
async def test_discover_company_domain_returns_none_on_no_token_overlap():
    search = FakeSearchProvider(
        [
            SearchResult(
                url="https://totallyunrelated.com/",
                title="Random Blog Post",
                snippet="This page has nothing to do with the query.",
            )
        ]
    )

    domain = await discover_company_domain(search, "Acme Robotics")

    assert domain is None
