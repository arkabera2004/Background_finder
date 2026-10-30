import pytest

from app.providers.company_crawler import FirecrawlCrawler, NullCrawler, build_company_crawler
from app.providers.search_provider import NullSearchProvider, TavilyProvider, build_search_provider


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


def test_build_search_provider_falls_back_to_null_without_key():
    provider = build_search_provider(tavily_api_key=None)
    assert isinstance(provider, NullSearchProvider)


def test_build_search_provider_uses_tavily_when_key_present():
    provider = build_search_provider(tavily_api_key="key")
    assert isinstance(provider, TavilyProvider)


def test_build_crawler_falls_back_to_null_without_key():
    crawler = build_company_crawler(firecrawl_api_key=None)
    assert isinstance(crawler, NullCrawler)


def test_build_crawler_uses_firecrawl_when_key_present():
    crawler = build_company_crawler(firecrawl_api_key="key")
    assert isinstance(crawler, FirecrawlCrawler)
