import httpx
import pytest

from app.providers.company_crawler import (
    FirecrawlCrawler,
    FirecrawlJobError,
    LocalExtractionCrawler,
    NullCrawler,
    build_company_crawler,
)
from app.providers.search_provider import (
    DuckDuckGoProvider,
    NullSearchProvider,
    SearXNGProvider,
    TavilyProvider,
    build_search_provider,
)


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self) -> dict:
        return self._payload


class _FakeFirecrawlClient:
    """Scripted responses for POST /v1/crawl then GET /v1/crawl/{id}, in
    call order, with no real network access."""

    responses: list[_FakeResponse] = []
    calls: list[dict] = []

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, url, headers=None, json=None):
        _FakeFirecrawlClient.calls.append({"method": "POST", "url": url, "json": json})
        return _FakeFirecrawlClient.responses.pop(0)

    async def get(self, url, headers=None):
        _FakeFirecrawlClient.calls.append({"method": "GET", "url": url})
        return _FakeFirecrawlClient.responses.pop(0)


@pytest.mark.asyncio
async def test_null_search_provider_returns_empty_not_fake_results():
    provider = NullSearchProvider()
    results = await provider.search("anything")
    assert results == []


@pytest.mark.asyncio
async def test_null_crawler_returns_empty_not_fake_pages():
    crawler = NullCrawler()
    pages = await crawler.crawl("example.com")
    assert pages == []


def test_build_search_provider_defaults_to_duckduckgo():
    provider = build_search_provider("duckduckgo")
    assert isinstance(provider, DuckDuckGoProvider)


def test_build_search_provider_tavily_falls_back_to_null_without_key():
    provider = build_search_provider("tavily", tavily_api_key=None)
    assert isinstance(provider, NullSearchProvider)


def test_build_search_provider_uses_tavily_when_key_present():
    provider = build_search_provider("tavily", tavily_api_key="key")
    assert isinstance(provider, TavilyProvider)


def test_build_search_provider_searxng_falls_back_to_null_without_url():
    provider = build_search_provider("searxng", searxng_base_url=None)
    assert isinstance(provider, NullSearchProvider)


def test_build_search_provider_uses_searxng_when_url_present():
    provider = build_search_provider("searxng", searxng_base_url="http://localhost:8080")
    assert isinstance(provider, SearXNGProvider)


@pytest.mark.asyncio
async def test_duckduckgo_search_is_live_and_returns_real_urls():
    """Real, live, keyless search — no mock. If this fails in an offline
    sandbox, that's a real network limitation, not a code defect; the
    provider must not fabricate results in that case (see below)."""
    provider = DuckDuckGoProvider()
    try:
        results = await provider.search("Python programming language", max_results=3)
    except RuntimeError:
        pytest.skip("No network access in this environment")
        return
    assert len(results) > 0
    assert all(r.url.startswith("http") for r in results)


def test_build_crawler_defaults_to_local_extraction():
    crawler = build_company_crawler("local")
    assert isinstance(crawler, LocalExtractionCrawler)


def test_build_crawler_firecrawl_falls_back_to_null_without_key():
    crawler = build_company_crawler("firecrawl", firecrawl_api_key=None)
    assert isinstance(crawler, NullCrawler)


def test_build_crawler_uses_firecrawl_when_key_present():
    crawler = build_company_crawler("firecrawl", firecrawl_api_key="key")
    assert isinstance(crawler, FirecrawlCrawler)


@pytest.mark.asyncio
async def test_firecrawl_crawl_submits_then_polls_until_completed(monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient", _FakeFirecrawlClient)
    _FakeFirecrawlClient.calls = []
    _FakeFirecrawlClient.responses = [
        _FakeResponse(200, {"success": True, "id": "job-1", "url": "https://api.firecrawl.dev/v1/crawl/job-1"}),
        _FakeResponse(
            200,
            {
                "status": "completed",
                "total": 1,
                "completed": 1,
                "data": [
                    {
                        "url": "https://example.com",
                        "markdown": "# Example\nSome content.",
                        "metadata": {"title": "Example Domain"},
                    }
                ],
            },
        ),
    ]

    crawler = FirecrawlCrawler(api_key="key", poll_interval_seconds=0)
    pages = await crawler.crawl("example.com")

    assert len(pages) == 1
    assert pages[0].url == "https://example.com"
    assert pages[0].title == "Example Domain"
    assert pages[0].text == "# Example\nSome content."
    assert _FakeFirecrawlClient.calls[0]["url"] == "https://api.firecrawl.dev/v1/crawl"
    assert _FakeFirecrawlClient.calls[1]["url"] == "https://api.firecrawl.dev/v1/crawl/job-1"


@pytest.mark.asyncio
async def test_firecrawl_crawl_polls_multiple_times_before_completion(monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient", _FakeFirecrawlClient)
    _FakeFirecrawlClient.calls = []
    _FakeFirecrawlClient.responses = [
        _FakeResponse(200, {"success": True, "id": "job-2"}),
        _FakeResponse(200, {"status": "scraping", "data": []}),
        _FakeResponse(200, {"status": "scraping", "data": []}),
        _FakeResponse(200, {"status": "completed", "data": [{"url": "https://example.com", "markdown": "done"}]}),
    ]

    crawler = FirecrawlCrawler(api_key="key", poll_interval_seconds=0)
    pages = await crawler.crawl("example.com")

    assert len(pages) == 1
    assert pages[0].text == "done"
    # 1 submit call + 3 status polls
    assert len(_FakeFirecrawlClient.calls) == 4


@pytest.mark.asyncio
async def test_firecrawl_crawl_failed_job_raises(monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient", _FakeFirecrawlClient)
    _FakeFirecrawlClient.calls = []
    _FakeFirecrawlClient.responses = [
        _FakeResponse(200, {"success": True, "id": "job-3"}),
        _FakeResponse(200, {"status": "failed", "error": "domain unreachable"}),
    ]

    crawler = FirecrawlCrawler(api_key="key", poll_interval_seconds=0)
    with pytest.raises(FirecrawlJobError):
        await crawler.crawl("example.com")


@pytest.mark.asyncio
async def test_firecrawl_crawl_times_out_without_returning_empty_silently(monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient", _FakeFirecrawlClient)
    _FakeFirecrawlClient.calls = []
    _FakeFirecrawlClient.responses = [
        _FakeResponse(200, {"success": True, "id": "job-4"}),
        _FakeResponse(200, {"status": "scraping", "data": []}),
        _FakeResponse(200, {"status": "scraping", "data": []}),
    ]

    crawler = FirecrawlCrawler(api_key="key", poll_interval_seconds=0, timeout_seconds=0)
    with pytest.raises(FirecrawlJobError, match="timed out"):
        await crawler.crawl("example.com")


@pytest.mark.asyncio
async def test_firecrawl_crawl_submission_http_error_raises(monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient", _FakeFirecrawlClient)
    _FakeFirecrawlClient.calls = []
    _FakeFirecrawlClient.responses = [_FakeResponse(401, text="unauthorized")]

    crawler = FirecrawlCrawler(api_key="bad-key", poll_interval_seconds=0)
    with pytest.raises(FirecrawlJobError):
        await crawler.crawl("example.com")


@pytest.mark.asyncio
async def test_firecrawl_crawl_status_check_http_error_raises(monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient", _FakeFirecrawlClient)
    _FakeFirecrawlClient.calls = []
    _FakeFirecrawlClient.responses = [
        _FakeResponse(200, {"success": True, "id": "job-5"}),
        _FakeResponse(500, text="server error"),
    ]

    crawler = FirecrawlCrawler(api_key="key", poll_interval_seconds=0)
    with pytest.raises(FirecrawlJobError):
        await crawler.crawl("example.com")


@pytest.mark.asyncio
async def test_firecrawl_crawl_missing_job_id_raises(monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient", _FakeFirecrawlClient)
    _FakeFirecrawlClient.calls = []
    _FakeFirecrawlClient.responses = [_FakeResponse(200, {"success": True})]

    crawler = FirecrawlCrawler(api_key="key", poll_interval_seconds=0)
    with pytest.raises(FirecrawlJobError, match="missing job id"):
        await crawler.crawl("example.com")


@pytest.mark.asyncio
async def test_firecrawl_crawl_malformed_status_response_raises(monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient", _FakeFirecrawlClient)
    _FakeFirecrawlClient.calls = []
    _FakeFirecrawlClient.responses = [
        _FakeResponse(200, {"success": True, "id": "job-6"}),
        _FakeResponse(200, {"total": 1}),  # no "status" field at all
    ]

    crawler = FirecrawlCrawler(api_key="key", poll_interval_seconds=0)
    with pytest.raises(FirecrawlJobError, match="missing 'status'"):
        await crawler.crawl("example.com")


def test_local_crawler_extracts_real_text_from_raw_html():
    """Deterministic, no network: proves trafilatura extraction itself
    works correctly, independent of any live site being reachable."""
    import trafilatura

    html = """
    <html><body>
    <nav>Home About Contact</nav>
    <article>
    <h1>Acme Corp</h1>
    <p>Acme Corp builds reliable distributed systems for enterprise customers.
    Our flagship product reduces latency by 40 percent across global regions.</p>
    </article>
    <footer>Copyright 2026</footer>
    </body></html>
    """
    extracted = trafilatura.extract(html, include_comments=False, include_tables=False)
    assert extracted is not None
    assert "Acme Corp builds reliable distributed systems" in extracted
    assert "Copyright" not in extracted  # footer noise correctly stripped
