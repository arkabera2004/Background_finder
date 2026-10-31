import httpx
import pytest

from app.providers.bright_data_provider import BrightDataProvider
from app.providers.pdl_provider import PDLProvider
from app.providers.profile_provider import ManualProvider, ProviderUnavailableError
from app.providers.selector import (
    ChainedProfileProvider,
    build_provider_chain,
    fetch_profile_with_fallback,
)


class _FakeResponse:
    def __init__(self, status_code: int, payload=None, text: str = ""):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.text = text

    def json(self):
        return self._payload


class _FakeBrightDataClient:
    """Scripted responses for POST /scrape then GET /progress/{id} and
    GET /snapshot/{id}, in call order, with no real network access."""

    responses: list[_FakeResponse] = []
    calls: list[dict] = []

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, url, params=None, headers=None, json=None):
        _FakeBrightDataClient.calls.append(
            {"method": "POST", "url": url, "params": params, "json": json}
        )
        return _FakeBrightDataClient.responses.pop(0)

    async def get(self, url, params=None, headers=None):
        _FakeBrightDataClient.calls.append({"method": "GET", "url": url, "params": params})
        return _FakeBrightDataClient.responses.pop(0)


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
async def test_manual_provider_prefers_explicit_full_name_over_guessed_text():
    """Regression: caught via a live curl request where a one-paragraph
    paste with no name supplied produced a garbled full_name. When the
    caller explicitly supplies full_name, it must win over any guess."""
    provider = ManualProvider()
    person = await provider.fetch_profile(
        linkedin_url=None,
        pasted_text="Jane Doe is a Senior Engineer at Acme who builds distributed systems.",
        full_name="Jane Doe",
    )
    assert person.full_name == "Jane Doe"


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
async def test_bright_data_requires_linkedin_url():
    provider = BrightDataProvider(api_key="key")
    with pytest.raises(ProviderUnavailableError):
        await provider.fetch_profile(linkedin_url=None, pasted_text="some text")


@pytest.mark.asyncio
async def test_bright_data_fast_sync_response_parses_profile(monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient", _FakeBrightDataClient)
    _FakeBrightDataClient.calls = []
    _FakeBrightDataClient.responses = [
        _FakeResponse(
            200,
            [{"name": "Satya Nadella", "position": "Chairman and CEO at Microsoft",
              "current_company": {"name": "Microsoft", "title": "Chairman and CEO"}}],
        )
    ]

    provider = BrightDataProvider(api_key="key")
    person = await provider.fetch_profile(
        linkedin_url="https://www.linkedin.com/in/satyanadella", pasted_text=None
    )

    assert person.full_name == "Satya Nadella"
    assert person.current_company == "Microsoft"
    assert person.headline == "Chairman and CEO at Microsoft"
    assert person.source == "bright_data"
    call = _FakeBrightDataClient.calls[0]
    assert call["params"] == {"dataset_id": "gd_l1viktl72bvl7bjuj0", "format": "json"}
    assert call["json"] == [{"url": "https://www.linkedin.com/in/satyanadella"}]


@pytest.mark.asyncio
async def test_bright_data_slow_job_polls_then_downloads(monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient", _FakeBrightDataClient)
    _FakeBrightDataClient.calls = []
    _FakeBrightDataClient.responses = [
        _FakeResponse(202, {"snapshot_id": "snap-1"}),
        _FakeResponse(200, {"status": "building"}),
        _FakeResponse(200, {"status": "building"}),
        _FakeResponse(200, {"status": "ready"}),
        _FakeResponse(200, [{"name": "Jane Doe"}]),
    ]

    provider = BrightDataProvider(api_key="key", poll_interval_seconds=0)
    person = await provider.fetch_profile(
        linkedin_url="https://linkedin.com/in/jane", pasted_text=None
    )

    assert person.full_name == "Jane Doe"
    assert len(_FakeBrightDataClient.calls) == 5


@pytest.mark.asyncio
async def test_bright_data_invalid_key_raises(monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient", _FakeBrightDataClient)
    _FakeBrightDataClient.calls = []
    _FakeBrightDataClient.responses = [_FakeResponse(401, text="unauthorized")]

    provider = BrightDataProvider(api_key="bad-key")
    with pytest.raises(ProviderUnavailableError):
        await provider.fetch_profile(linkedin_url="https://linkedin.com/in/x", pasted_text=None)


@pytest.mark.asyncio
async def test_bright_data_snapshot_failed_raises(monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient", _FakeBrightDataClient)
    _FakeBrightDataClient.calls = []
    _FakeBrightDataClient.responses = [
        _FakeResponse(202, {"snapshot_id": "snap-2"}),
        _FakeResponse(200, {"status": "failed"}),
    ]

    provider = BrightDataProvider(api_key="key", poll_interval_seconds=0)
    with pytest.raises(ProviderUnavailableError):
        await provider.fetch_profile(linkedin_url="https://linkedin.com/in/x", pasted_text=None)


@pytest.mark.asyncio
async def test_bright_data_snapshot_timeout_raises(monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient", _FakeBrightDataClient)
    _FakeBrightDataClient.calls = []
    _FakeBrightDataClient.responses = [
        _FakeResponse(202, {"snapshot_id": "snap-3"}),
        _FakeResponse(200, {"status": "building"}),
    ]

    provider = BrightDataProvider(api_key="key", poll_interval_seconds=0, timeout_seconds=0)
    with pytest.raises(ProviderUnavailableError, match="timed out"):
        await provider.fetch_profile(linkedin_url="https://linkedin.com/in/x", pasted_text=None)


@pytest.mark.asyncio
async def test_bright_data_empty_records_raises(monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient", _FakeBrightDataClient)
    _FakeBrightDataClient.calls = []
    _FakeBrightDataClient.responses = [_FakeResponse(200, [])]

    provider = BrightDataProvider(api_key="key")
    with pytest.raises(ProviderUnavailableError):
        await provider.fetch_profile(linkedin_url="https://linkedin.com/in/x", pasted_text=None)


@pytest.mark.asyncio
async def test_bright_data_missing_name_field_raises(monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient", _FakeBrightDataClient)
    _FakeBrightDataClient.calls = []
    _FakeBrightDataClient.responses = [_FakeResponse(200, [{"position": "no name here"}])]

    provider = BrightDataProvider(api_key="key")
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


@pytest.mark.asyncio
async def test_chained_profile_provider_falls_back_to_manual_without_keys():
    """Covers research_service.py's actual FetchProfileStage wiring: with no
    paid keys configured, a pasted-text request still succeeds via Manual."""
    provider = ChainedProfileProvider(bright_data_api_key=None, pdl_api_key=None)
    person = await provider.fetch_profile(
        linkedin_url=None, pasted_text="Jane Doe\nEngineer at Acme"
    )
    assert person.source == "manual"


@pytest.mark.asyncio
async def test_chained_profile_provider_uses_bright_data_when_configured(monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient", _FakeBrightDataClient)
    _FakeBrightDataClient.calls = []
    _FakeBrightDataClient.responses = [_FakeResponse(200, [{"name": "Jane Doe"}])]

    provider = ChainedProfileProvider(bright_data_api_key="key", pdl_api_key=None)
    person = await provider.fetch_profile(
        linkedin_url="https://linkedin.com/in/jane", pasted_text=None
    )
    assert person.source == "bright_data"


def test_settings_reads_bright_data_key_from_brightdata_env_var(monkeypatch):
    """Regression: pydantic-settings' default mapping for the Python field
    `bright_data_api_key` is the env var `BRIGHT_DATA_API_KEY`, but the
    actual/documented var is `BRIGHTDATA_API_KEY` (no underscore, matching
    Bright Data's own name) — without the field's validation_alias this
    silently reads as empty with no error, which happened live in session."""
    monkeypatch.setenv("BRIGHTDATA_API_KEY", "live-test-key")
    from app.core.config import Settings

    assert Settings().bright_data_api_key == "live-test-key"
