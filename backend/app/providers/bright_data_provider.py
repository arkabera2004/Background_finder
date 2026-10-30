from app.providers.profile_provider import ProfileProvider, ProviderUnavailableError
from app.schemas.profile import Person


class BrightDataProvider(ProfileProvider):
    """Bright Data LinkedIn Scraper API adapter.

    BLOCKED: requires a Bright Data account and API key (BRIGHTDATA_API_KEY),
    which do not exist yet, and the mandated 20-profile trial evaluation
    (see docs/PROVIDER_EVALUATION.md) has not been run. This adapter raises
    rather than returning a fabricated response.
    """

    name = "bright_data"

    def __init__(self, api_key: str | None):
        self.api_key = api_key

    async def fetch_profile(self, linkedin_url: str | None, pasted_text: str | None) -> Person:
        if not self.api_key:
            raise ProviderUnavailableError(
                "Bright Data provider has no API key configured (BRIGHTDATA_API_KEY)."
            )
        raise NotImplementedError(
            "Bright Data integration is not implemented pending the 20-profile trial "
            "and account provisioning. See docs/PROVIDER_EVALUATION.md."
        )
