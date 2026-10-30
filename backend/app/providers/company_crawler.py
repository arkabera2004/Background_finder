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


class LocalExtractionCrawler(CompanyCrawler):
    """Free default: fetches pages itself and extracts with trafilatura.

    Respects robots.txt, stays on the same domain, caps pages and per-page
    timeout. This is what makes company research work with zero paid
    crawling service — the tradeoff is JS-rendered pages won't extract
    well (no headless browser here; Playwright is a documented future
    upgrade, not implemented this session — see docs/KNOWN_LIMITATIONS.md).
    """

    name = "local"

    def __init__(self, page_timeout_seconds: float = 20.0):
        self.page_timeout_seconds = page_timeout_seconds

    def _robots_allows(self, domain: str, path: str) -> bool:
        import urllib.robotparser

        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(f"https://{domain}/robots.txt")
        try:
            rp.read()
        except Exception:  # noqa: BLE001 - missing/unreachable robots.txt means "no restriction"
            return True
        return rp.can_fetch("*", f"https://{domain}{path}")

    async def crawl(self, domain: str, max_pages: int = 15) -> list[CrawledPage]:
        import httpx
        import trafilatura

        paths = ["/", "/about", "/about-us", "/products", "/pricing", "/blog"][:max_pages]
        pages: list[CrawledPage] = []

        async with httpx.AsyncClient(
            timeout=self.page_timeout_seconds, follow_redirects=True
        ) as client:
            for path in paths:
                if not self._robots_allows(domain, path):
                    continue
                url = f"https://{domain}{path}"
                try:
                    resp = await client.get(url)
                except httpx.HTTPError:
                    continue
                if resp.status_code != 200:
                    continue

                extracted = trafilatura.extract(
                    resp.text, include_comments=False, include_tables=False
                )
                if not extracted:
                    continue
                title = trafilatura.extract_metadata(resp.text)
                pages.append(
                    CrawledPage(
                        url=url,
                        title=title.title if title else None,
                        text=extracted,
                    )
                )
        return pages


def build_company_crawler(
    provider_name: str = "local", firecrawl_api_key: str | None = None
) -> CompanyCrawler:
    choice = provider_name.lower()
    if choice == "firecrawl":
        if not firecrawl_api_key:
            return NullCrawler()
        return FirecrawlCrawler(firecrawl_api_key)
    if choice == "local":
        return LocalExtractionCrawler()
    return NullCrawler()
