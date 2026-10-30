from abc import ABC, abstractmethod

from pydantic import BaseModel


class CrawledPage(BaseModel):
    url: str
    title: str | None = None
    text: str


class CompanyCrawler(ABC):
    name: str

    @abstractmethod
    async def crawl(self, domain: str, max_pages: int = 15) -> list[CrawledPage]: ...


class NullCrawler(CompanyCrawler):
    """Honest no-op: returns zero pages rather than fabricating company facts.

    Used when FIRECRAWL_API_KEY is not configured. research_company then
    correctly reports "no sources" instead of inventing a company profile.
    """

    name = "null"

    async def crawl(self, domain: str, max_pages: int = 15) -> list[CrawledPage]:
        return []


class FirecrawlCrawler(CompanyCrawler):
    """BLOCKED: requires FIRECRAWL_API_KEY. Not called without one."""

    name = "firecrawl"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def crawl(self, domain: str, max_pages: int = 15) -> list[CrawledPage]:
        import httpx

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.firecrawl.dev/v1/crawl",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"url": f"https://{domain}", "limit": max_pages},
            )
            resp.raise_for_status()
            data = resp.json()
        return [
            CrawledPage(
                url=p.get("url", domain),
                title=p.get("metadata", {}).get("title"),
                text=p.get("markdown", ""),
            )
            for p in data.get("data", [])[:max_pages]
        ]


def build_company_crawler(firecrawl_api_key: str | None) -> CompanyCrawler:
    if firecrawl_api_key:
        return FirecrawlCrawler(firecrawl_api_key)
    return NullCrawler()
