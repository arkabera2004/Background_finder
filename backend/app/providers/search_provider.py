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


def build_search_provider(tavily_api_key: str | None) -> SearchProvider:
    if tavily_api_key:
        return TavilyProvider(tavily_api_key)
    return NullSearchProvider()
