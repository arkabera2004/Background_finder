from app.core.config import Settings
from app.providers.ai_provider import AiProvider
from app.providers.anthropic_provider import AnthropicProvider
from app.providers.gemini_provider import GeminiProvider
from app.providers.ollama_provider import OllamaProvider


class UnknownAiProviderError(ValueError):
    pass


def build_ai_provider(settings: Settings) -> AiProvider:
    """Picks the active provider from config. Never silently picks a paid
    provider — `ai_provider` must be explicitly set to "anthropic"."""
    choice = settings.ai_provider.lower()

    if choice == "gemini":
        return GeminiProvider(settings.gemini_api_key, model=settings.gemini_model)
    if choice == "ollama":
        return OllamaProvider(settings.ollama_base_url, model=settings.ollama_model)
    if choice == "anthropic":
        return AnthropicProvider(settings.anthropic_api_key, model=settings.claude_model_fast)

    raise UnknownAiProviderError(
        f"Unknown ai_provider '{settings.ai_provider}'. Expected gemini, ollama, or anthropic."
    )
