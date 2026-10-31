import json

import pytest

from app.providers.ai_provider import AiProviderUnavailableError, Completion, Usage
from app.schemas.brief import Source
from app.services.ai_brief_synthesizer import rule_based_synthesis, synthesize_with_ai


class FakeAiProvider:
    """A scripted AiProvider — no network, no mocking framework needed,
    just a fake implementing the same interface real providers do."""

    name = "fake"

    def __init__(self, responses: list[str]):
        self._responses = responses
        self.calls = 0
        self.last_timeout_seconds: float | None = None

    async def complete(self, prompt: str, *, max_tokens: int = 1024, timeout_seconds: float = 30.0):
        self.last_timeout_seconds = timeout_seconds
        response_text = self._responses[self.calls]
        self.calls += 1
        return Completion(
            text=response_text,
            model="fake-model",
            provider=self.name,
            usage=Usage(input_tokens=100, output_tokens=50, estimated_cost_usd=0.001),
        )

    async def health_check(self) -> bool:
        return True


VALID_SOURCE = Source(id="s0", url="https://example.com/talk", title="Conference Talk")

VALID_RESPONSE = json.dumps(
    {
        "prospect_name": "Jane Doe",
        "snapshot": [
            {"text": "Senior Engineer at Acme", "source_ids": ["s0"], "confidence": "high", "is_inference": False}
        ],
        "career_story": [],
        "current_role": [],
        "company": [],
        "content_and_interests": [],
        "communication_style": [],
        "likely_priorities": [],
        "hooks": [{"text": "Spoke at a conference", "source_ids": ["s0"], "confidence": "medium"}],
        "dos_and_donts": [],
    }
)


@pytest.mark.asyncio
async def test_ai_synthesis_produces_valid_brief_with_metadata():
    provider = FakeAiProvider([VALID_RESPONSE])
    brief, metadata = await synthesize_with_ai(
        provider, {"full_name": "Jane Doe"}, {}, [VALID_SOURCE]
    )

    assert brief.prospect_name == "Jane Doe"
    assert len(brief.snapshot) == 1
    assert metadata["synthesis_method"] == "ai"
    assert metadata["provider"] == "fake"
    assert metadata["input_tokens"] == 100
    assert metadata["estimated_cost_usd"] == 0.001


@pytest.mark.asyncio
async def test_ai_synthesis_drops_claim_with_fabricated_source_id():
    """The model cites a source_id that was never provided. The citation
    validator must drop that claim rather than trust the model's claim."""
    fabricated_response = json.dumps(
        {
            "prospect_name": "Jane Doe",
            "snapshot": [
                {
                    "text": "Won an award the model made up",
                    "source_ids": ["fake-source-id-999"],
                    "confidence": "high",
                    "is_inference": False,
                }
            ],
            "career_story": [],
            "current_role": [],
            "company": [],
            "content_and_interests": [],
            "communication_style": [],
            "likely_priorities": [],
            "hooks": [],
            "dos_and_donts": [],
        }
    )
    provider = FakeAiProvider([fabricated_response])
    brief, _ = await synthesize_with_ai(provider, {"full_name": "Jane Doe"}, {}, [VALID_SOURCE])

    assert brief.snapshot == []  # fabricated-citation claim dropped


@pytest.mark.asyncio
async def test_ai_synthesis_uses_a_generous_timeout():
    """Regression: a real live call against gemini-3.8-flash (a "thinking"
    model) timed out in session with the provider's 30s default — a
    structured-JSON synthesis prompt routinely takes over a minute. This
    must request a timeout well above that default, not rely on it."""
    provider = FakeAiProvider([VALID_RESPONSE])
    await synthesize_with_ai(provider, {"full_name": "Jane Doe"}, {}, [VALID_SOURCE])

    assert provider.last_timeout_seconds is not None
    assert provider.last_timeout_seconds >= 60.0


@pytest.mark.asyncio
async def test_ai_synthesis_retries_once_on_invalid_json_then_succeeds():
    provider = FakeAiProvider(["not valid json at all", VALID_RESPONSE])
    brief, metadata = await synthesize_with_ai(
        provider, {"full_name": "Jane Doe"}, {}, [VALID_SOURCE]
    )

    assert provider.calls == 2
    assert brief.prospect_name == "Jane Doe"


@pytest.mark.asyncio
async def test_ai_synthesis_raises_after_two_invalid_attempts():
    from app.providers.ai_provider import AiProviderError

    provider = FakeAiProvider(["garbage", "still garbage"])
    with pytest.raises(AiProviderError):
        await synthesize_with_ai(provider, {"full_name": "Jane Doe"}, {}, [VALID_SOURCE])


@pytest.mark.asyncio
async def test_ai_synthesis_handles_markdown_fenced_json():
    fenced = f"```json\n{VALID_RESPONSE}\n```"
    provider = FakeAiProvider([fenced])
    brief, _ = await synthesize_with_ai(provider, {"full_name": "Jane Doe"}, {}, [VALID_SOURCE])
    assert brief.prospect_name == "Jane Doe"


def test_rule_based_synthesis_still_works_identically():
    brief, metadata = rule_based_synthesis({"full_name": "Jane Doe", "headline": "Engineer"}, {}, [])
    assert brief.prospect_name == "Jane Doe"
    assert metadata["synthesis_method"] == "rule_based"
    assert metadata["provider"] is None


@pytest.mark.asyncio
async def test_unavailable_provider_raises_and_caller_can_fall_back():
    class UnavailableProvider:
        name = "unavailable"

        async def complete(self, *args, **kwargs):
            raise AiProviderUnavailableError("no key configured")

        async def health_check(self) -> bool:
            return False

    with pytest.raises(AiProviderUnavailableError):
        await synthesize_with_ai(UnavailableProvider(), {"full_name": "Jane"}, {}, [])
