"""Local Ollama provider — zero cost, zero cloud dependency.

https://ollama.com/ — requires `ollama serve` running locally (default
http://localhost:11434) with a model pulled (e.g. `ollama pull llama3.2`).
This is the path that makes the Free Basic Plan work with NO internet AI
API at all, at the cost of needing local compute.
"""

import httpx

from app.providers.ai_provider import (
    AiProvider,
    AiProviderError,
    AiProviderUnavailableError,
    AiTimeoutError,
    Completion,
    Usage,
)


class OllamaProvider(AiProvider):
    name = "ollama"

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.2"):
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def complete(
        self, prompt: str, *, max_tokens: int = 1024, timeout_seconds: float = 60.0
    ) -> Completion:
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                resp = await client.post(
                    f"{self.base_url}/api/generate",
                    json={"model": self.model, "prompt": prompt, "stream": False},
                )
        except httpx.ConnectError as exc:
            raise AiProviderUnavailableError(
                f"Ollama not reachable at {self.base_url} — is `ollama serve` running?"
            ) from exc
        except httpx.TimeoutException as exc:
            raise AiTimeoutError(str(exc)) from exc

        if resp.status_code == 404:
            raise AiProviderUnavailableError(
                f"Model '{self.model}' not pulled. Run: ollama pull {self.model}"
            )
        if resp.status_code != 200:
            raise AiProviderError(f"Ollama error {resp.status_code}: {resp.text}")

        data = resp.json()
        input_tokens = data.get("prompt_eval_count", 0)
        output_tokens = data.get("eval_count", 0)

        return Completion(
            text=data.get("response", ""),
            model=self.model,
            provider=self.name,
            usage=Usage(input_tokens=input_tokens, output_tokens=output_tokens, estimated_cost_usd=0.0),
        )

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
            return resp.status_code == 200
        except httpx.HTTPError:
            return False
