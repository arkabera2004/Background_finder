import pytest

from app.providers.search_provider import SearchResult
from app.services.identity_resolution import find_identity_candidates


class FakeSearch:
    def __init__(self, results: list[SearchResult]):
        self._results = results

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        return self._results


@pytest.mark.asyncio
async def test_unique_match_returns_single_candidate():
    search = FakeSearch(
        [SearchResult(url="https://linkedin.com/in/jane-doe-1", title="Jane Doe - Acme")]
    )
    candidates = await find_identity_candidates("Jane Doe", "Acme", search)
    assert len(candidates) == 1
    assert candidates[0].linkedin_url == "https://linkedin.com/in/jane-doe-1"


@pytest.mark.asyncio
async def test_ambiguous_match_returns_multiple_distinct_candidates():
    search = FakeSearch(
        [
            SearchResult(url="https://linkedin.com/in/jane-doe-1", title="Jane Doe - Engineer at Acme"),
            SearchResult(url="https://linkedin.com/in/jane-doe-2", title="Jane Doe - Sales at Acme"),
        ]
    )
    candidates = await find_identity_candidates("Jane Doe", "Acme", search)
    assert len(candidates) == 2
    assert candidates[0].title != candidates[1].title


@pytest.mark.asyncio
async def test_no_match_returns_empty_list_not_fabricated_candidate():
    search = FakeSearch([])
    candidates = await find_identity_candidates("Nobody Real", "Nowhere Inc", search)
    assert candidates == []


@pytest.mark.asyncio
async def test_non_profile_urls_are_filtered_out():
    search = FakeSearch(
        [
            SearchResult(url="https://linkedin.com/company/acme", title="Acme company page"),
            SearchResult(url="https://example.com/blog", title="Unrelated blog"),
        ]
    )
    candidates = await find_identity_candidates("Jane Doe", "Acme", search)
    assert candidates == []


@pytest.mark.asyncio
async def test_duplicate_urls_are_deduplicated():
    search = FakeSearch(
        [
            SearchResult(url="https://linkedin.com/in/jane-doe-1", title="Jane Doe - Acme"),
            SearchResult(url="https://linkedin.com/in/jane-doe-1", title="Jane Doe - Acme (cached)"),
        ]
    )
    candidates = await find_identity_candidates("Jane Doe", "Acme", search)
    assert len(candidates) == 1


@pytest.mark.asyncio
async def test_candidate_not_mentioning_the_company_is_rejected_as_noise():
    """Regression: a site:-scoped search can surface a profile that
    merely co-occurs with both search terms (e.g. someone else's
    LinkedIn activity feed) without being evidence this person works at
    the target company — confirmed live on run 24882912-... producing
    unrelated namesakes in several candidate lists."""
    search = FakeSearch(
        [
            SearchResult(url="https://linkedin.com/in/jane-doe-1", title="Jane Doe - VP at Acme Corp"),
            SearchResult(url="https://linkedin.com/in/unrelated-jane", title="Jane Doe - Designer"),
        ]
    )
    candidates = await find_identity_candidates("Jane Doe", "Acme Corp", search)
    assert len(candidates) == 1
    assert candidates[0].linkedin_url == "https://linkedin.com/in/jane-doe-1"
