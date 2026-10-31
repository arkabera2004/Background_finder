import pytest

from app.providers.search_provider import SearchProvider, SearchResult
from app.services import company_discovery
from app.services.company_discovery import discover_company_domain


class FakeSearchProvider(SearchProvider):
    name = "fake"

    def __init__(self, results: list[SearchResult]):
        self._results = results

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        return self._results


@pytest.fixture(autouse=True)
def _safe_dns(monkeypatch):
    """Default all hostname resolution in these tests to a safe public IP,
    so plausibility-match tests aren't incidentally testing DNS/network
    behaviour. Individual tests override this to exercise SSRF rejection."""
    monkeypatch.setattr(company_discovery.socket, "gethostbyname", lambda host: "93.184.216.34")


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


@pytest.mark.asyncio
async def test_discover_company_domain_rejects_generic_word_only_match():
    """A shared generic word like 'Solutions' must not be enough to match
    an otherwise unrelated company."""
    search = FakeSearchProvider(
        [
            SearchResult(
                url="https://unrelatedsolutions.example/",
                title="Totally Unrelated Solutions - Official Website",
                snippet="We provide generic business solutions.",
            )
        ]
    )

    domain = await discover_company_domain(search, "Initech Solutions Inc")

    assert domain is None


@pytest.mark.asyncio
async def test_discover_company_domain_matches_on_distinctive_token_in_third_result():
    """A distinctive token match in result #2 or #3 (not just #1) should
    still be accepted."""
    search = FakeSearchProvider(
        [
            SearchResult(
                url="https://unrelated-one.example/",
                title="Random Unrelated Business",
                snippet="Nothing to do with the query.",
            ),
            SearchResult(
                url="https://unrelated-two.example/",
                title="Another Unrelated Business",
                snippet="Still nothing relevant.",
            ),
            SearchResult(
                url="https://acmerobotics.com/about",
                title="Acme Robotics - Official Website",
                snippet="Acme Robotics builds industrial robots.",
            ),
        ]
    )

    domain = await discover_company_domain(search, "Acme Robotics")

    assert domain == "acmerobotics.com"


@pytest.mark.asyncio
async def test_discover_company_domain_rejects_loopback_resolution(monkeypatch):
    monkeypatch.setattr(company_discovery.socket, "gethostbyname", lambda host: "127.0.0.1")
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

    assert domain is None


@pytest.mark.asyncio
async def test_discover_company_domain_rejects_link_local_metadata_resolution(monkeypatch):
    monkeypatch.setattr(company_discovery.socket, "gethostbyname", lambda host: "169.254.169.254")
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

    assert domain is None


@pytest.mark.asyncio
async def test_discover_company_domain_rejects_dns_resolution_failure(monkeypatch):
    def _raise(host):
        raise OSError("name resolution failed")

    monkeypatch.setattr(company_discovery.socket, "gethostbyname", _raise)
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

    assert domain is None
