import pytest

from app.providers.company_crawler import (
    FirecrawlCrawler,
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
