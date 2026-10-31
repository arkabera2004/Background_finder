import httpx
import pytest

from app.core.config import Settings
from app.providers.ai_provider import AiProviderError, AiProviderUnavailableError, AiRateLimitError
from app.providers.ai_selector import UnknownAiProviderError, build_ai_provider
from app.providers.anthropic_provider import AnthropicProvider
from app.providers.gemini_provider import GeminiProvider


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("POST", "https://example.com")
            response = httpx.Response(self.status_code, text=self.text, request=request)
            raise httpx.HTTPStatusError(
                f"status {self.status_code}", request=request, response=response
            )


class _FakeAsyncClient:
    """Captures the request made by the provider under test so assertions
    can run without any real network call."""

    last_request: dict | None = None
    responses: list[_FakeResponse] = []

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, url, json=None, headers=None):
        _FakeAsyncClient.last_request = {"method": "POST", "url": url, "json": json, "headers": headers}
        return _FakeAsyncClient.responses.pop(0)

    async def get(self, url, headers=None):
        _FakeAsyncClient.last_request = {"method": "GET", "url": url, "headers": headers}
        return _FakeAsyncClient.responses.pop(0)


@pytest.mark.asyncio
async def test_gemini_health_check_false_without_key():
    provider = GeminiProvider(api_key="")
    assert await provider.health_check() is False


@pytest.mark.asyncio
async def test_gemini_complete_raises_without_key():
    provider = GeminiProvider(api_key="")
    with pytest.raises(AiProviderUnavailableError):
        await provider.complete("hello")


@pytest.mark.asyncio
async def test_gemini_complete_success_parses_response(monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)
    _FakeAsyncClient.responses = [
        _FakeResponse(
            200,
            {
                "candidates": [{"content": {"parts": [{"text": "hi there"}]}}],
                "usageMetadata": {"promptTokenCount": 3, "candidatesTokenCount": 5},
            },
        )
    ]

    provider = GeminiProvider(api_key="k", model="gemini-2.0-flash")
    result = await provider.complete("hello")

    assert result.text == "hi there"
    assert result.model == "gemini-2.0-flash"
    assert result.provider == "gemini"
    assert result.usage.input_tokens == 3
    assert result.usage.output_tokens == 5


@pytest.mark.asyncio
async def test_gemini_complete_raises_on_api_error(monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)
    _FakeAsyncClient.responses = [_FakeResponse(400, text="bad request")]

    provider = GeminiProvider(api_key="k", max_retries=0)
    with pytest.raises(AiProviderError):
        await provider.complete("hello")


@pytest.mark.asyncio
async def test_gemini_complete_raises_rate_limit_after_retries(monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)
    monkeypatch.setattr("asyncio.sleep", lambda *_args, **_kwargs: _noop_sleep())
    _FakeAsyncClient.responses = [
        _FakeResponse(429, text="rate limited"),
        _FakeResponse(429, text="rate limited"),
    ]

    provider = GeminiProvider(api_key="k", max_retries=1)
    with pytest.raises(AiRateLimitError):
        await provider.complete("hello")


@pytest.mark.asyncio
async def test_gemini_complete_raises_on_malformed_response(monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)
    _FakeAsyncClient.responses = [_FakeResponse(200, {"unexpected": "shape"})]

    provider = GeminiProvider(api_key="k")
    with pytest.raises(AiProviderError):
        await provider.complete("hello")


@pytest.mark.asyncio
async def test_gemini_complete_raises_clean_error_on_max_tokens_with_no_content(monkeypatch):
    """Reproduces a real, live-observed response shape from gemini-3.8-flash:
    a "thinking" model can spend the whole token budget on reasoning and
    return a candidate with finishReason=MAX_TOKENS and no content.parts —
    this must raise AiProviderError, not KeyError."""
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)
    _FakeAsyncClient.responses = [
        _FakeResponse(
            200,
            {
                "candidates": [{"content": {}, "finishReason": "MAX_TOKENS", "index": 0}],
                "usageMetadata": {"promptTokenCount": 2, "totalTokenCount": 19},
            },
        )
    ]

    provider = GeminiProvider(api_key="k", model="gemini-3.8-flash")
    with pytest.raises(AiProviderError, match="MAX_TOKENS"):
        await provider.complete("hello", max_tokens=20)


async def _noop_sleep():
    return None


@pytest.mark.asyncio
async def test_anthropic_health_check_false_without_key():
    provider = AnthropicProvider(api_key="")
    assert await provider.health_check() is False


def test_selector_builds_gemini_by_default():
    settings = Settings(ai_provider="gemini", gemini_api_key="k")
    provider = build_ai_provider(settings)
    assert isinstance(provider, GeminiProvider)


def test_selector_builds_anthropic_only_when_explicitly_chosen():
    settings = Settings(ai_provider="anthropic", anthropic_api_key="k")
    provider = build_ai_provider(settings)
    assert isinstance(provider, AnthropicProvider)


def test_selector_rejects_unknown_provider():
    settings = Settings(ai_provider="chatgpt")
    with pytest.raises(UnknownAiProviderError):
        build_ai_provider(settings)


def test_selector_rejects_ollama_now_unsupported():
    """Regression guard: Ollama support was removed — "ollama" must no
    longer resolve to a working provider."""
    settings = Settings(ai_provider="ollama")
    with pytest.raises(UnknownAiProviderError):
        build_ai_provider(settings)
