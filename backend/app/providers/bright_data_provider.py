from app.providers.profile_provider import ProfileProvider, ProviderUnavailableError
from app.schemas.profile import Person

# Bright Data's LinkedIn "People Profile" dataset — see
# https://docs.brightdata.com/products/scrapers/linkedin/quickstart
LINKEDIN_PROFILE_DATASET_ID = "gd_l1viktl72bvl7bjuj0"
API_BASE = "https://api.brightdata.com/datasets/v3"


class BrightDataProvider(ProfileProvider):
    """Bright Data LinkedIn Scraper API adapter.

    POST /datasets/v3/scrape returns the profile directly (200) for a fast
    job, or a snapshot_id (202) for a slow one — in which case this polls
    GET /datasets/v3/progress/{id} until "ready"/"failed" (bounded by
    timeout_seconds) and downloads via GET /datasets/v3/snapshot/{id}.

    Note: the mandated 20-profile coverage/cost trial in
    docs/PROVIDER_EVALUATION.md has not been run — this makes the
    integration work, it does not substitute for that evaluation before
    committing to production spend.
    """

    name = "bright_data"

    def __init__(
        self,
        api_key: str | None,
        poll_interval_seconds: float = 3.0,
        timeout_seconds: float = 120.0,
    ):
        self.api_key = api_key
        self.poll_interval_seconds = poll_interval_seconds
        self.timeout_seconds = timeout_seconds

    async def fetch_profile(
        self, linkedin_url: str | None, pasted_text: str | None, full_name: str | None = None
    ) -> Person:
        if not self.api_key:
            raise ProviderUnavailableError(
                "Bright Data provider has no API key configured (BRIGHTDATA_API_KEY)."
            )
        if not linkedin_url:
            raise ProviderUnavailableError(
                "Bright Data requires a linkedin_url; none was supplied."
            )

        import httpx

        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        # Bright Data holds a synchronous /scrape request open up to ~60s
        # before falling back to the async 202+snapshot_id path, so the
        # client timeout here must clear that, not just typical API latency.
        async with httpx.AsyncClient(timeout=90) as client:
            resp = await client.post(
                f"{API_BASE}/scrape",
                params={"dataset_id": LINKEDIN_PROFILE_DATASET_ID, "format": "json"},
                headers=headers,
                json=[{"url": linkedin_url}],
            )

        if resp.status_code == 401:
            raise ProviderUnavailableError("Bright Data rejected the API key (401).")
        if resp.status_code == 200:
            records = resp.json()
        elif resp.status_code == 202:
            snapshot_id = resp.json().get("snapshot_id")
            if not snapshot_id:
                raise ProviderUnavailableError(
                    f"Bright Data accepted the job but returned no snapshot_id: {resp.text}"
                )
            records = await self._poll_and_download(snapshot_id, headers)
        else:
            raise ProviderUnavailableError(f"Bright Data error {resp.status_code}: {resp.text}")

        return self._parse(records, linkedin_url)

    async def _poll_and_download(self, snapshot_id: str, headers: dict) -> list:
        import asyncio

        import httpx

        elapsed = 0.0
        async with httpx.AsyncClient(timeout=30) as client:
            while True:
                progress_resp = await client.get(
                    f"{API_BASE}/progress/{snapshot_id}", headers=headers
                )
                if progress_resp.status_code != 200:
                    raise ProviderUnavailableError(
                        f"Bright Data progress check failed: "
                        f"{progress_resp.status_code} {progress_resp.text}"
                    )
                status = progress_resp.json().get("status")

                if status == "ready":
                    download_resp = await client.get(
                        f"{API_BASE}/snapshot/{snapshot_id}",
                        params={"format": "json"},
                        headers=headers,
                    )
                    if download_resp.status_code != 200:
                        raise ProviderUnavailableError(
                            f"Bright Data snapshot download failed: "
                            f"{download_resp.status_code} {download_resp.text}"
                        )
                    return download_resp.json()
                if status == "failed":
                    raise ProviderUnavailableError(f"Bright Data snapshot {snapshot_id} failed.")
                if status is None:
                    raise ProviderUnavailableError(
                        f"Bright Data progress response missing 'status': {progress_resp.text}"
                    )

                if elapsed >= self.timeout_seconds:
                    raise ProviderUnavailableError(
                        f"Bright Data snapshot {snapshot_id} timed out after "
                        f"{self.timeout_seconds}s (last status: {status})"
                    )
                await asyncio.sleep(self.poll_interval_seconds)
                elapsed += self.poll_interval_seconds

    def _parse(self, records: list, linkedin_url: str) -> Person:
        if not records:
            raise ProviderUnavailableError(f"Bright Data returned no profile for {linkedin_url}")
        record = records[0]
        name = record.get("name")
        if not name:
            raise ProviderUnavailableError(
                f"Bright Data response missing a 'name' field: {record}"
            )

        current_company = record.get("current_company") or {}
        headline = record.get("position") or current_company.get("title")

        return Person(
            full_name=name,
            headline=headline,
            current_company=current_company.get("name"),
            linkedin_url=linkedin_url,
            source=self.name,
        )
