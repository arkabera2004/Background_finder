import pytest

from app.providers.bright_data_provider import BrightDataProvider
from app.providers.pdl_provider import PDLProvider
from app.providers.profile_provider import ManualProvider, ProviderUnavailableError
from app.providers.selector import build_provider_chain, fetch_profile_with_fallback


@pytest.mark.asyncio
async def test_manual_provider_builds_person_from_pasted_text():
    provider = ManualProvider()
    person = await provider.fetch_profile(
        linkedin_url=None,
        pasted_text="Jane Doe\nSenior Engineer at Acme\nBuilds things.",
    )
    assert person.full_name == "Jane Doe"
    assert person.headline == "Senior Engineer at Acme"
    assert person.source == "manual"


@pytest.mark.asyncio
async def test_manual_provider_requires_pasted_text():
    provider = ManualProvider()
    with pytest.raises(ProviderUnavailableError):
        await provider.fetch_profile(linkedin_url="https://linkedin.com/in/x", pasted_text=None)


@pytest.mark.asyncio
async def test_bright_data_unavailable_without_key():
    provider = BrightDataProvider(api_key=None)
    with pytest.raises(ProviderUnavailableError):
        await provider.fetch_profile(linkedin_url="https://linkedin.com/in/x", pasted_text=None)


@pytest.mark.asyncio
async def test_pdl_unavailable_without_key():
    provider = PDLProvider(api_key=None)
    with pytest.raises(ProviderUnavailableError):
        await provider.fetch_profile(linkedin_url="https://linkedin.com/in/x", pasted_text=None)


def test_provider_chain_always_ends_in_manual():
    chain = build_provider_chain(bright_data_api_key=None, pdl_api_key=None)
    assert len(chain) == 1
    assert chain[0].name == "manual"


def test_provider_chain_prefers_paid_providers_first():
    chain = build_provider_chain(bright_data_api_key="key", pdl_api_key="key")
    assert [p.name for p in chain] == ["bright_data", "pdl", "manual"]


@pytest.mark.asyncio
async def test_fetch_with_fallback_reaches_manual_when_paid_unconfigured():
    chain = build_provider_chain(bright_data_api_key=None, pdl_api_key=None)
    person = await fetch_profile_with_fallback(
        chain, linkedin_url=None, pasted_text="Jane Doe\nEngineer"
    )
    assert person.source == "manual"
