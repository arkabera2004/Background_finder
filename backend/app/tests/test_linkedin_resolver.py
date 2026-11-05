from app.providers.search_provider import SearchProvider, SearchResult
from app.services.linkedin_resolver import resolve_person_identity


class FakeSearchProvider(SearchProvider):
    name = "fake"

    def __init__(self, urls: list[str]):
        self._urls = urls

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        return [SearchResult(url=url, title="Jane Doe - CEO - Acme") for url in self._urls]


async def test_resolve_confirms_when_exactly_one_candidate():
    search = FakeSearchProvider(["https://linkedin.com/in/janedoe"])

    outcome = await resolve_person_identity(search, "Jane Doe", "Acme")

    assert outcome["resolution_status"] == "confirmed"
    assert outcome["linkedin_url"] == "https://linkedin.com/in/janedoe"
    assert len(outcome["candidate_profiles"]) == 1


async def test_resolve_flags_ambiguous_when_multiple_candidates():
    search = FakeSearchProvider(["https://linkedin.com/in/janedoe", "https://linkedin.com/in/janedoe2"])

    outcome = await resolve_person_identity(search, "Jane Doe", "Acme")

    assert outcome["resolution_status"] == "ambiguous"
    assert outcome["linkedin_url"] is None
    assert len(outcome["candidate_profiles"]) == 2


async def test_resolve_flags_unresolved_when_no_candidates():
    search = FakeSearchProvider([])

    outcome = await resolve_person_identity(search, "Jane Doe", "Acme")

    assert outcome["resolution_status"] == "unresolved"
    assert outcome["linkedin_url"] is None
    assert outcome["candidate_profiles"] == []
