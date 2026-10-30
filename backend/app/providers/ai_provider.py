"""Common AI provider interface. Model names are never hardcoded in callers —
every caller asks for a structured completion and gets back typed, costed,
usage-tracked output regardless of which provider answers it.

Free-first: Gemini's free tier and local Ollama are first-class, not
afterthoughts. Anthropic is an optional premium provider (see
app/providers/anthropic_provider.py) and is never required for the Free
Basic Plan — app/core/config.py's `ai_provider` setting picks which one
is active, so switching is a config change, not a code change.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


class AiProviderError(Exception):
    """Base class for all AI provider failures (timeout, rate limit, auth, etc)."""


class AiProviderUnavailableError(AiProviderError):
    """No credentials configured / provider unreachable (e.g. Ollama not running)."""


class AiRateLimitError(AiProviderError):
    pass


class AiTimeoutError(AiProviderError):
    pass


@dataclass
class Usage:
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float


@dataclass
class Completion:
    text: str
    model: str
    provider: str
    usage: Usage


class AiProvider(ABC):
    name: str

    @abstractmethod
    async def complete(
        self, prompt: str, *, max_tokens: int = 1024, timeout_seconds: float = 30.0
    ) -> Completion: ...

    @abstractmethod
    async def health_check(self) -> bool: ...
