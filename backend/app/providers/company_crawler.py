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


class FirecrawlJobError(RuntimeError):
    """The Firecrawl crawl job failed, timed out, or returned something the
    app can't parse. Raised rather than returning an empty page list, so a
    crawl failure is visible instead of silently looking like "no sources"."""


class FirecrawlCrawler(CompanyCrawler):
    """BLOCKED: requires FIRECRAWL_API_KEY. Not called without one.

    POST /v1/crawl starts an async job (returns a job id, not pages); the
    result must be fetched by polling GET /v1/crawl/{id} until status is
    "completed" or "failed". See https://docs.firecrawl.dev/api-reference/endpoint/crawl-get
    """

    name = "firecrawl"

    def __init__(
        self,
        api_key: str,
        poll_interval_seconds: float = 2.0,
        timeout_seconds: float = 60.0,
    ):
        self.api_key = api_key
        self.poll_interval_seconds = poll_interval_seconds
        self.timeout_seconds = timeout_seconds

    async def crawl(self, domain: str, max_pages: int = 15) -> list[CrawledPage]:
        import asyncio

        import httpx

        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(timeout=30) as client:
            start_resp = await client.post(
                "https://api.firecrawl.dev/v1/crawl",
                headers=headers,
                json={"url": f"https://{domain}", "limit": max_pages},
            )
            if start_resp.status_code != 200:
                raise FirecrawlJobError(
                    f"Firecrawl crawl submission failed: {start_resp.status_code} {start_resp.text}"
                )
            start_data = start_resp.json()
            job_id = start_data.get("id")
            if not job_id:
                raise FirecrawlJobError(f"Firecrawl crawl response missing job id: {start_data}")

            elapsed = 0.0
            while True:
                status_resp = await client.get(
                    f"https://api.firecrawl.dev/v1/crawl/{job_id}", headers=headers
                )
                if status_resp.status_code != 200:
                    raise FirecrawlJobError(
                        f"Firecrawl crawl status check failed: {status_resp.status_code} {status_resp.text}"
                    )
                status_data = status_resp.json()
                status = status_data.get("status")

                if status == "completed":
                    return [
                        CrawledPage(
                            url=p.get("url") or p.get("metadata", {}).get("sourceURL", domain),
                            title=p.get("metadata", {}).get("title"),
                            text=p.get("markdown", ""),
                        )
                        for p in status_data.get("data", [])[:max_pages]
                    ]
                if status == "failed":
                    raise FirecrawlJobError(f"Firecrawl crawl job {job_id} failed: {status_data}")
                if status is None:
                    raise FirecrawlJobError(
                        f"Firecrawl crawl status response missing 'status': {status_data}"
                    )

                if elapsed >= self.timeout_seconds:
                    raise FirecrawlJobError(
                        f"Firecrawl crawl job {job_id} timed out after {self.timeout_seconds}s "
                        f"(last status: {status})"
                    )
                await asyncio.sleep(self.poll_interval_seconds)
                elapsed += self.poll_interval_seconds


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

        paths = [
            "/",
            "/about",
            "/about-us",
            "/products",
            "/pricing",
            "/news",
            "/press",
            "/newsroom",
            "/blog",
        ][:max_pages]
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
