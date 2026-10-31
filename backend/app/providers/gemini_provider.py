"""Google Gemini provider — free tier is the default AI path for the Basic Plan.

https://ai.google.dev/gemini-api/docs — the free tier (as of this writing)
covers gemini-3.8-flash and similar models at generous per-minute/per-day
limits for development use. Model name is configurable
(GEMINI_MODEL, default "gemini-3.8-flash") — never hardcoded elsewhere.

gemini-3.8-flash and later "thinking" models can spend the entire
maxOutputTokens budget on internal reasoning and return a candidate with
no `content.parts` at all (`finishReason: "MAX_TOKENS"`). That's treated
as an empty, not malformed, response below — not a KeyError.
"""

import asyncio

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

# Free tier is $0 — cost tracking reports 0 for Gemini unless a future paid
# tier config is added. Never invented: Gemini's billed pricing differs by
# tier and model, and this app defaults to the free tier.
GEMINI_COST_PER_TOKEN_USD = 0.0

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiProvider(AiProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str = "gemini-3.8-flash", max_retries: int = 2):
        self.api_key = api_key
        self.model = model
        self.max_retries = max_retries

    async def complete(
        self, prompt: str, *, max_tokens: int = 1024, timeout_seconds: float = 30.0
    ) -> Completion:
        if not self.api_key:
            raise AiProviderUnavailableError("GEMINI_API_KEY is not configured.")

        url = f"{GEMINI_API_BASE}/{self.model}:generateContent?key={self.api_key}"
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": max_tokens},
        }

        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                    resp = await client.post(url, json=body)
                if resp.status_code == 429:
                    raise AiRateLimitError(f"Gemini rate limited: {resp.text}")
                resp.raise_for_status()
                data = resp.json()
                break
            except httpx.TimeoutException as exc:
                last_exc = AiTimeoutError(str(exc))
            except AiRateLimitError as exc:
                last_exc = exc
            except httpx.HTTPStatusError as exc:
                raise AiProviderError(f"Gemini error {exc.response.status_code}: {exc.response.text}") from exc

            if attempt < self.max_retries:
                await asyncio.sleep(2**attempt)
        else:
            raise last_exc or AiProviderError("Gemini request failed after retries")

        candidates = data.get("candidates") or []
        if not candidates:
            raise AiProviderError(f"Gemini returned no candidates: {data}")
        parts = candidates[0].get("content", {}).get("parts")
        if not parts:
            finish_reason = candidates[0].get("finishReason", "unknown")
            raise AiProviderError(
                f"Gemini returned no content (finishReason={finish_reason}); "
                "the model may have used its entire token budget on internal "
                "reasoning — retry with a larger max_tokens."
            )
        text = parts[0].get("text", "")
        usage_meta = data.get("usageMetadata", {})
        input_tokens = usage_meta.get("promptTokenCount", 0)
        output_tokens = usage_meta.get("candidatesTokenCount", 0)

        return Completion(
            text=text,
            model=self.model,
            provider=self.name,
            usage=Usage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                estimated_cost_usd=(input_tokens + output_tokens) * GEMINI_COST_PER_TOKEN_USD,
            ),
        )

    async def health_check(self) -> bool:
        if not self.api_key:
            return False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{GEMINI_API_BASE}?key={self.api_key}")
            return resp.status_code == 200
        except httpx.HTTPError:
            return False
