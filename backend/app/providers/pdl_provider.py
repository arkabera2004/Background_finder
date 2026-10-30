from app.providers.profile_provider import ProfileProvider, ProviderUnavailableError
from app.schemas.profile import Person


class PDLProvider(ProfileProvider):
    """People Data Labs adapter.

    BLOCKED: requires a PDL account and API key (PDL_API_KEY), which do not
    exist yet, and the mandated 20-profile trial evaluation (see
    docs/PROVIDER_EVALUATION.md) has not been run.
    """

    name = "pdl"

    def __init__(self, api_key: str | None):
        self.api_key = api_key

    async def fetch_profile(self, linkedin_url: str | None, pasted_text: str | None) -> Person:
        if not self.api_key:
            raise ProviderUnavailableError("PDL provider has no API key configured (PDL_API_KEY).")
        raise NotImplementedError(
            "People Data Labs integration is not implemented pending the 20-profile "
            "trial and account provisioning. See docs/PROVIDER_EVALUATION.md."
        )
