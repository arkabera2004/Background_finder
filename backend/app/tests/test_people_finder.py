from app.providers.search_provider import SearchProvider, SearchResult
from app.services.people_finder import (
    discover_people_for_company,
    extract_name_from_result_title,
    score_confidence,
    select_leaders,
)


class FakeSearchProvider(SearchProvider):
    name = "fake"

    def __init__(self, results_by_query: dict[str, list[SearchResult]]):
        self._results_by_query = results_by_query

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        return self._results_by_query.get(query, [])


def test_extract_name_from_result_title_parses_linkedin_format():
    assert extract_name_from_result_title("Jane Doe - CEO - Acme Corp | LinkedIn") == "Jane Doe"
    assert extract_name_from_result_title("Acme Corp | LinkedIn") is None
    assert extract_name_from_result_title(None) is None


def test_score_confidence_rewards_linkedin_url_company_and_role_match():
    assert score_confidence("https://linkedin.com/in/janedoe", "Jane Doe - CEO - Acme", "Acme", "CEO") == 1.0
    assert score_confidence("https://example.com/bio", "Jane Doe", "Acme", "CEO") == 0.0


async def test_discover_people_for_company_dedupes_by_name():
    results = {
        '"Acme" CEO linkedin': [
            SearchResult(url="https://linkedin.com/in/janedoe", title="Jane Doe - CEO - Acme | LinkedIn"),
        ],
        '"Acme" CTO linkedin': [
            # same person surfaces again under a different role query
            SearchResult(url="https://linkedin.com/in/janedoe", title="Jane Doe - CEO - Acme | LinkedIn"),
            SearchResult(url="https://linkedin.com/in/johnsmith", title="John Smith - CTO - Acme | LinkedIn"),
        ],
    }
    search = FakeSearchProvider(results)

    candidates = await discover_people_for_company(search, "Acme", roles=["CEO", "CTO"])

    assert len(candidates) == 2
    names = {c["full_name"] for c in candidates}
    assert names == {"Jane Doe", "John Smith"}
    assert all(c["identity_confirmed"] is False for c in candidates)


async def test_discover_people_rejects_non_profile_urls():
    """Regression for the false-positive people found live on run
    24882912-3ff9-4b78-8d59-be945e636b41: a tracxn.com company directory
    page, a LinkedIn *post* (not a profile), and an investor-tracking
    site all surfaced for a role query and were persisted as "people"
    because only the title shape was checked, never the URL."""
    results = {
        '"Acme" CEO linkedin': [
            # a company directory page, title shaped like a person
            SearchResult(url="https://tracxn.com/d/companies/cio-connect", title="CIO Connect - CEO - Acme | LinkedIn"),
            # a LinkedIn post, not a profile
            SearchResult(
                url="https://www.linkedin.com/posts/vaiaadvisory_thesis-activity-123",
                title="India's Late - CEO - Acme | LinkedIn",
            ),
            # an unrelated investor-tracking site
            SearchResult(url="https://signal.nfx.com/investors/tomasz-tunguz", title="Tomasz Tunguz - CEO - Acme"),
            # the one real result
            SearchResult(url="https://linkedin.com/in/janedoe", title="Jane Doe - CEO - Acme | LinkedIn"),
        ],
    }
    search = FakeSearchProvider(results)

    candidates = await discover_people_for_company(search, "Acme", roles=["CEO"])

    assert len(candidates) == 1
    assert candidates[0]["full_name"] == "Jane Doe"


async def test_discover_people_rejects_organisation_shaped_names_even_with_a_profile_url():
    """Defense in depth: even if a result were a linkedin.com/in/ URL, a
    name containing a whole-word organisation indicator (not a plausible
    human name component) is rejected — e.g. "Kafum Engineering"."""
    results = {
        '"Acme" VP Engineering linkedin': [
            SearchResult(
                url="https://linkedin.com/in/kafum-engineering", title="Kafum Engineering - VP Engineering - Acme"
            ),
            SearchResult(url="https://linkedin.com/in/realvp", title="Alex Rivera - VP Engineering - Acme"),
        ],
    }
    search = FakeSearchProvider(results)

    candidates = await discover_people_for_company(search, "Acme", roles=["VP Engineering"])

    assert len(candidates) == 1
    assert candidates[0]["full_name"] == "Alex Rivera"


def test_select_leaders_ranks_by_confidence_and_caps():
    candidates = [
        {"full_name": "A", "confidence": 0.3},
        {"full_name": "B", "confidence": 0.9},
        {"full_name": "C", "confidence": 0.6},
    ]

    top_two = select_leaders(candidates, 2)

    assert [c["full_name"] for c in top_two] == ["B", "C"]
