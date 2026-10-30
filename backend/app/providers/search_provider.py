from abc import ABC, abstractmethod

from pydantic import BaseModel


class SearchResult(BaseModel):
    url: str
    title: str | None = None
    snippet: str | None = None


class SearchProvider(ABC):
    name: str

    @abstractmethod
    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]: ...


class NullSearchProvider(SearchProvider):
    """Honest no-op: returns zero results rather than fabricating sources.

    Used when no TAVILY_API_KEY/EXA_API_KEY is configured. Never invents a
    URL or snippet — an empty list is the correct, truthful output here.
    """

    name = "null"

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        return []


class TavilyProvider(SearchProvider):
    """BLOCKED: requires TAVILY_API_KEY. Not called without one."""

    name = "tavily"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        import httpx

        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                json={"api_key": self.api_key, "query": query, "max_results": max_results},
            )
            resp.raise_for_status()
            data = resp.json()
        return [
            SearchResult(url=r["url"], title=r.get("title"), snippet=r.get("content"))
            for r in data.get("results", [])[:max_results]
        ]


class DuckDuckGoProvider(SearchProvider):
    """Free, keyless web search via the `ddgs` library.

    No account, no API key, no guaranteed SLA — DuckDuckGo may rate-limit
    or change its HTML without notice, which is why this never raises on
    "no results," only on a hard transport failure. This is the default
    search provider for the Free Basic Plan.
    """

    name = "duckduckgo"

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        import asyncio

        from ddgs import DDGS

        def _run() -> list[dict]:
            with DDGS() as ddgs:
                return list(ddgs.text(query, max_results=max_results))

        try:
            raw = await asyncio.to_thread(_run)
        except Exception as exc:  # noqa: BLE001 - ddgs has no stable exception hierarchy
            raise RuntimeError(f"DuckDuckGo search failed: {exc}") from exc

        return [
            SearchResult(url=r.get("href", ""), title=r.get("title"), snippet=r.get("body"))
            for r in raw
            if r.get("href")
        ]


class SearXNGProvider(SearchProvider):
    """Self-hosted SearXNG instance. https://docs.searxng.org/

    BLOCKED until a SEARXNG_BASE_URL is configured and reachable — no
    public SearXNG instance is used by default (most disallow programmatic
    use by anonymous clients).
    """

    name = "searxng"

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        import httpx

        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(
                f"{self.base_url}/search", params={"q": query, "format": "json"}
            )
            resp.raise_for_status()
            data = resp.json()
        return [
            SearchResult(url=r["url"], title=r.get("title"), snippet=r.get("content"))
            for r in data.get("results", [])[:max_results]
        ]


def build_search_provider(
    provider_name: str,
    tavily_api_key: str | None = None,
    searxng_base_url: str | None = None,
) -> SearchProvider:
    choice = provider_name.lower()
    if choice == "duckduckgo":
        return DuckDuckGoProvider()
    if choice == "searxng":
        if not searxng_base_url:
            return NullSearchProvider()
        return SearXNGProvider(searxng_base_url)
    if choice == "tavily":
        if not tavily_api_key:
            return NullSearchProvider()
        return TavilyProvider(tavily_api_key)
    return NullSearchProvider()
