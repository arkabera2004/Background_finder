"""Anthropic — optional premium provider. Never required for the Free Basic
Plan; app/providers/ai_selector.py never picks this one unless the active
plan/config explicitly asks for it and a key is present.
"""

import httpx

from app.providers.ai_provider import (
    AiProvider,
    AiProviderError,
    AiProviderUnavailableError,
    AiRateLimitError,
    AiTimeoutError,
    Completion,
    Usage,
)

# Approximate Claude Haiku pricing per the published rate card; update if it
# changes. Not used for Gemini-free-tier or Ollama paths.
ANTHROPIC_INPUT_COST_PER_TOKEN_USD = 0.0000008
ANTHROPIC_OUTPUT_COST_PER_TOKEN_USD = 0.000004


class AnthropicProvider(AiProvider):
    name = "anthropic"

    def __init__(self, api_key: str, model: str = "claude-haiku-4-5-20251001"):
        self.api_key = api_key
        self.model = model

    async def complete(
        self, prompt: str, *, max_tokens: int = 1024, timeout_seconds: float = 30.0
    ) -> Completion:
        if not self.api_key:
            raise AiProviderUnavailableError("ANTHROPIC_API_KEY is not configured.")

        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "max_tokens": max_tokens,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                )
        except httpx.TimeoutException as exc:
            raise AiTimeoutError(str(exc)) from exc

        if resp.status_code == 429:
            raise AiRateLimitError(f"Anthropic rate limited: {resp.text}")
        if resp.status_code != 200:
            raise AiProviderError(f"Anthropic error {resp.status_code}: {resp.text}")

        data = resp.json()
        text = "".join(block.get("text", "") for block in data.get("content", []))
        usage = data.get("usage", {})
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)

        return Completion(
            text=text,
            model=self.model,
            provider=self.name,
            usage=Usage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                estimated_cost_usd=(
                    input_tokens * ANTHROPIC_INPUT_COST_PER_TOKEN_USD
                    + output_tokens * ANTHROPIC_OUTPUT_COST_PER_TOKEN_USD
                ),
            ),
        )

    async def health_check(self) -> bool:
        return bool(self.api_key)
