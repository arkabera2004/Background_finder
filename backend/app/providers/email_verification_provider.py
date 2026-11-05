"""Agent 05 (Email Hunter) verification providers.

Same honesty convention as search_provider.py: a null/unconfigured
provider returns "unknown", never fabricates a "valid" result.
"""

from abc import ABC, abstractmethod

from pydantic import BaseModel


class EmailVerificationResult(BaseModel):
    status: str  # "valid" | "invalid" | "unknown"
    confidence: float


class EmailVerificationProvider(ABC):
    name: str

    @abstractmethod
    async def verify(self, email: str) -> EmailVerificationResult: ...


class NullEmailVerificationProvider(EmailVerificationProvider):
    """No provider configured: every candidate stays "unknown" rather than
    being guessed into "valid" — callers must route these to manual review,
    never treat them as sendable."""

    name = "null"

    async def verify(self, email: str) -> EmailVerificationResult:
        return EmailVerificationResult(status="unknown", confidence=0.0)


class NeverBounceProvider(EmailVerificationProvider):
    """BLOCKED: requires NEVERBOUNCE_API_KEY. Not called without one."""

    name = "neverbounce"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def verify(self, email: str) -> EmailVerificationResult:
        import httpx

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://api.neverbounce.com/v4/single/check",
                params={"key": self.api_key, "email": email},
            )
            resp.raise_for_status()
            data = resp.json()

        result = data.get("result", "unknown")
        status = {"valid": "valid", "invalid": "invalid"}.get(result, "unknown")
        confidence = 0.9 if status == "valid" else (0.9 if status == "invalid" else 0.0)
        return EmailVerificationResult(status=status, confidence=confidence)


def build_email_verification_provider(provider_name: str, neverbounce_api_key: str | None = None) -> EmailVerificationProvider:
    choice = provider_name.lower()
    if choice == "neverbounce":
        if not neverbounce_api_key:
            return NullEmailVerificationProvider()
        return NeverBounceProvider(neverbounce_api_key)
    return NullEmailVerificationProvider()
