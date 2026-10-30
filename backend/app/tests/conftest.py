import pytest

from app.core.config import settings


@pytest.fixture(autouse=True)
def _no_live_network_by_default(monkeypatch):
    """Keep the test suite fast and deterministic: default search_provider
    is "duckduckgo" in production (free, keyless), but hitting the real
    network on every pipeline test makes the suite slow and flaky under
    DuckDuckGo rate limiting. Tests that specifically want to exercise a
    live provider (e.g. test_duckduckgo_search_is_live_and_returns_real_urls)
    construct that provider directly, bypassing this setting entirely.
    """
    monkeypatch.setattr(settings, "search_provider", "tavily")
    monkeypatch.setattr(settings, "tavily_api_key", "")
    monkeypatch.setattr(settings, "extraction_provider", "firecrawl")
    monkeypatch.setattr(settings, "firecrawl_api_key", "")
