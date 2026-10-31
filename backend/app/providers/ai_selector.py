from app.core.config import Settings
from app.providers.ai_provider import AiProvider
from app.providers.anthropic_provider import AnthropicProvider
from app.providers.gemini_provider import GeminiProvider


class UnknownAiProviderError(ValueError):
    pass


def build_ai_provider(settings: Settings) -> AiProvider:
    """Picks the active provider from config. Gemini is the only free/default
    provider; Anthropic remains available but never auto-selected — `ai_provider`
    must be explicitly set to "anthropic". Ollama support was removed."""
    choice = settings.ai_provider.lower()

    if choice == "gemini":
        return GeminiProvider(settings.gemini_api_key, model=settings.gemini_model)
    if choice == "anthropic":
        return AnthropicProvider(settings.anthropic_api_key, model=settings.claude_model_fast)

    raise UnknownAiProviderError(
        f"Unknown ai_provider '{settings.ai_provider}'. Expected gemini or anthropic."
    )
