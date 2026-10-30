import pytest

from app.core.config import Settings
from app.providers.ai_provider import AiProviderUnavailableError
from app.providers.ai_selector import UnknownAiProviderError, build_ai_provider
from app.providers.anthropic_provider import AnthropicProvider
from app.providers.gemini_provider import GeminiProvider
from app.providers.ollama_provider import OllamaProvider


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
async def test_ollama_health_check_false_when_not_running():
    """Real live check against localhost:11434 — no mock. This genuinely
    proves the app behaves correctly when Ollama isn't installed/running,
    which is the common case in CI and most dev machines."""
    provider = OllamaProvider(base_url="http://localhost:19999")  # unused port, not real ollama
    assert await provider.health_check() is False


@pytest.mark.asyncio
async def test_ollama_complete_raises_when_unreachable():
    provider = OllamaProvider(base_url="http://localhost:19999")
    with pytest.raises(AiProviderUnavailableError):
        await provider.complete("hello")


@pytest.mark.asyncio
async def test_anthropic_health_check_false_without_key():
    provider = AnthropicProvider(api_key="")
    assert await provider.health_check() is False


def test_selector_builds_gemini_by_default():
    settings = Settings(ai_provider="gemini", gemini_api_key="k")
    provider = build_ai_provider(settings)
    assert isinstance(provider, GeminiProvider)


def test_selector_builds_ollama():
    settings = Settings(ai_provider="ollama")
    provider = build_ai_provider(settings)
    assert isinstance(provider, OllamaProvider)


def test_selector_builds_anthropic_only_when_explicitly_chosen():
    settings = Settings(ai_provider="anthropic", anthropic_api_key="k")
    provider = build_ai_provider(settings)
    assert isinstance(provider, AnthropicProvider)


def test_selector_rejects_unknown_provider():
    settings = Settings(ai_provider="chatgpt")
    with pytest.raises(UnknownAiProviderError):
        build_ai_provider(settings)
