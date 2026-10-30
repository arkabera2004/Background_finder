from app.providers.bright_data_provider import BrightDataProvider
from app.providers.pdl_provider import PDLProvider
from app.providers.profile_provider import ManualProvider, ProfileProvider, ProviderUnavailableError


def build_provider_chain(
    bright_data_api_key: str | None, pdl_api_key: str | None
) -> list[ProfileProvider]:
    """Ordered provider preference: paid providers first if configured, manual always last."""
    chain: list[ProfileProvider] = []
    if bright_data_api_key:
        chain.append(BrightDataProvider(bright_data_api_key))
    if pdl_api_key:
        chain.append(PDLProvider(pdl_api_key))
    chain.append(ManualProvider())
    return chain


async def fetch_profile_with_fallback(
    providers: list[ProfileProvider],
    linkedin_url: str | None,
    pasted_text: str | None,
    full_name: str | None = None,
):
    last_error: Exception | None = None
    for provider in providers:
        try:
            return await provider.fetch_profile(linkedin_url, pasted_text, full_name)
        except (ProviderUnavailableError, NotImplementedError) as exc:
            last_error = exc
            continue
    raise ProviderUnavailableError(
        f"All providers in the chain failed; last error: {last_error}"
    )
