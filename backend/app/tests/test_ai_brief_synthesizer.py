import json

import pytest

from app.providers.ai_provider import AiProviderError, AiProviderUnavailableError, Completion, Usage
from app.schemas.brief import Source
from app.services.ai_brief_synthesizer import build_prompt, rule_based_synthesis, synthesize_with_ai
from app.services.citation_validator import validate_brief


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


def _valid_brief_dict(**overrides: object) -> dict:
    base: dict[str, object] = {
        "prospect_name": "Jane Doe",
        "snapshot": [
            {"text": "Senior Engineer at Acme", "source_ids": ["s0"], "confidence": "high", "is_inference": False}
        ],
        "current_role": [],
        "company_overview": [],
        "career_timeline": [],
        "expertise": [],
        "activity": [],
        "recurring_themes": [],
        "company_context": [],
        "communication_style": [],
        "likely_priorities": [],
        "personalization_hooks": [
            {
                "evidence": "Spoke at a conference",
                "relevance": "Shows thought leadership",
                "outreach_angle": "Ask about the talk",
                "source_ids": ["s0"],
                "confidence": "medium",
            }
        ],
        "outreach_strategy": {"angle": None, "primary_hooks": [], "avoid": []},
        "research_gaps": {},
    }
    base.update(overrides)
    return base


VALID_RESPONSE = json.dumps(_valid_brief_dict())


# ---------------------------------------------------------------------------
# build_prompt
# ---------------------------------------------------------------------------


def test_build_prompt_contains_new_section_names_and_anti_fabrication_rules():
    prompt = build_prompt({"full_name": "Jane"}, {"career_timeline": []}, [], [VALID_SOURCE])

    for section in (
        "company_overview",
        "career_timeline",
        "activity",
        "recurring_themes",
        "company_context",
        "personalization_hooks",
        "outreach_strategy",
        "research_gaps",
    ):
        assert section in prompt

    assert "do not invent dates" in prompt.lower() or "do not invent" in prompt.lower()
    assert "conflicting_information" in prompt


def test_build_prompt_describes_optional_date_field_on_claims():
    prompt = build_prompt({"full_name": "Jane"}, {"career_timeline": []}, [], [VALID_SOURCE])

    assert '"date"' in prompt


def test_build_prompt_includes_company_gaps_block_when_provided():
    prompt = build_prompt(
        {"full_name": "Jane"},
        {"career_timeline": []},
        [],
        [VALID_SOURCE],
        ["Could not confidently identify Acme's official website"],
    )

    assert "KNOWN RESEARCH GAPS" in prompt
    assert "Could not confidently identify Acme's official website" in prompt


# ---------------------------------------------------------------------------
# synthesize_with_ai
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ai_synthesis_produces_valid_brief_with_metadata():
    provider = FakeAiProvider([VALID_RESPONSE])
    brief, metadata = await synthesize_with_ai(
        provider, {"full_name": "Jane Doe"}, {"career_timeline": []}, [], [VALID_SOURCE]
    )

    assert brief.prospect_name == "Jane Doe"
    assert len(brief.snapshot) == 1
    assert metadata["synthesis_method"] == "ai"
    assert metadata["provider"] == "fake"
    assert metadata["input_tokens"] == 100
    assert metadata["estimated_cost_usd"] == 0.001


@pytest.mark.asyncio
async def test_ai_synthesis_populates_career_timeline_and_activity():
    response = json.dumps(
        _valid_brief_dict(
            career_timeline=[
                {
                    "organization": "Acme",
                    "title": "Senior Engineer",
                    "start_date": "2020-01",
                    "end_date": None,
                    "description": None,
                    "source_ids": ["s0"],
                    "confidence": "medium",
                }
            ],
            activity=[
                {
                    "activity_type": "original_post",
                    "topic": "AI",
                    "summary": "Posted about AI",
                    "url": "https://example.com/post",
                    "published_at": None,
                    "authored_by_person": True,
                    "relevance": None,
                    "confidence": "medium",
                    "source_ids": ["s0"],
                }
            ],
        )
    )
    provider = FakeAiProvider([response])
    brief, _ = await synthesize_with_ai(
        provider, {"full_name": "Jane Doe"}, {"career_timeline": []}, [], [VALID_SOURCE]
    )

    assert len(brief.career_timeline) == 1
    assert brief.career_timeline[0].organization == "Acme"
    assert len(brief.activity) == 1
    assert brief.activity[0].topic == "AI"


@pytest.mark.asyncio
async def test_ai_synthesis_drops_claim_with_fabricated_source_id():
    """The model cites a source_id that was never provided. The citation
    validator must drop that claim rather than trust the model's claim."""
    fabricated_response = json.dumps(
        _valid_brief_dict(
            snapshot=[
                {
                    "text": "Won an award the model made up",
                    "source_ids": ["fake-source-id-999"],
                    "confidence": "high",
                    "is_inference": False,
                }
            ],
            personalization_hooks=[],
        )
    )
    provider = FakeAiProvider([fabricated_response])
    brief, _ = await synthesize_with_ai(
        provider, {"full_name": "Jane Doe"}, {"career_timeline": []}, [], [VALID_SOURCE]
    )

    assert brief.snapshot == []  # fabricated-citation claim dropped


@pytest.mark.asyncio
async def test_ai_synthesis_uses_a_generous_timeout():
    """Regression: a real live call against gemini-3.8-flash (a "thinking"
    model) timed out in session with the provider's 30s default — a
    structured-JSON synthesis prompt routinely takes over a minute. This
    must request a timeout well above that default, not rely on it."""
    provider = FakeAiProvider([VALID_RESPONSE])
    await synthesize_with_ai(provider, {"full_name": "Jane Doe"}, {"career_timeline": []}, [], [VALID_SOURCE])

    assert provider.last_timeout_seconds is not None
    assert provider.last_timeout_seconds >= 60.0


@pytest.mark.asyncio
async def test_ai_synthesis_retries_once_on_invalid_json_then_succeeds():
    provider = FakeAiProvider(["not valid json at all", VALID_RESPONSE])
    brief, metadata = await synthesize_with_ai(
        provider, {"full_name": "Jane Doe"}, {"career_timeline": []}, [], [VALID_SOURCE]
    )

    assert provider.calls == 2
    assert brief.prospect_name == "Jane Doe"


@pytest.mark.asyncio
async def test_ai_synthesis_raises_after_two_invalid_attempts():
    provider = FakeAiProvider(["garbage", "still garbage"])
    with pytest.raises(AiProviderError):
        await synthesize_with_ai(provider, {"full_name": "Jane Doe"}, {"career_timeline": []}, [], [VALID_SOURCE])


@pytest.mark.asyncio
async def test_ai_synthesis_raises_on_syntactically_truncated_json_both_attempts():
    """Review Focus #1: a Gemini MAX_TOKENS response that's cut off
    mid-field (syntactically invalid JSON) must raise after the retry,
    never be silently accepted as a half-filled brief."""
    truncated = '{"prospect_name": "Jane Doe", "snapshot": [{"text": "Senior Eng'
    provider = FakeAiProvider([truncated, truncated])
    with pytest.raises(AiProviderError):
        await synthesize_with_ai(provider, {"full_name": "Jane Doe"}, {"career_timeline": []}, [], [VALID_SOURCE])
    assert provider.calls == 2


@pytest.mark.asyncio
async def test_ai_synthesis_handles_markdown_fenced_json():
    fenced = f"```json\n{VALID_RESPONSE}\n```"
    provider = FakeAiProvider([fenced])
    brief, _ = await synthesize_with_ai(
        provider, {"full_name": "Jane Doe"}, {"career_timeline": []}, [], [VALID_SOURCE]
    )
    assert brief.prospect_name == "Jane Doe"


@pytest.mark.asyncio
async def test_ai_synthesis_with_empty_sources_produces_empty_lists_not_fabrication():
    """Review Focus #2 (AI path): empty research input must degrade to
    empty lists, never fabricated placeholders."""
    response = json.dumps(
        _valid_brief_dict(
            snapshot=[],
            personalization_hooks=[],
            research_gaps={"missing_information": ["No sources were found"]},
        )
    )
    provider = FakeAiProvider([response])
    brief, _ = await synthesize_with_ai(provider, {"full_name": "Jane Doe"}, {"career_timeline": []}, [], [])

    assert brief.career_timeline == []
    assert brief.activity == []
    assert brief.recurring_themes == []
    assert brief.research_gaps.missing_information == ["No sources were found"]


@pytest.mark.asyncio
async def test_ai_synthesis_conflicting_career_facts_produce_research_gap_entry():
    """Review Focus #4: verified via a fixture provider returning a
    conflict note, not the real model's behavior."""
    response = json.dumps(
        _valid_brief_dict(
            research_gaps={
                "conflicting_information": [
                    "Source A says role started 2019-01; Source B says 2020-03 — kept both, not resolved."
                ]
            }
        )
    )
    provider = FakeAiProvider([response])
    brief, _ = await synthesize_with_ai(
        provider, {"full_name": "Jane Doe"}, {"career_timeline": []}, [], [VALID_SOURCE]
    )

    assert len(brief.research_gaps.conflicting_information) == 1
    assert "2019-01" in brief.research_gaps.conflicting_information[0]


@pytest.mark.asyncio
async def test_unavailable_provider_raises_and_caller_can_fall_back():
    class UnavailableProvider:
        name = "unavailable"

        async def complete(self, *args, **kwargs):
            raise AiProviderUnavailableError("no key configured")

        async def health_check(self) -> bool:
            return False

    with pytest.raises(AiProviderUnavailableError):
        await synthesize_with_ai(UnavailableProvider(), {"full_name": "Jane"}, {"career_timeline": []}, [], [])


# ---------------------------------------------------------------------------
# rule_based_synthesis
# ---------------------------------------------------------------------------


def test_rule_based_synthesis_still_works_with_basic_person_data():
    brief, metadata = rule_based_synthesis(
        {"full_name": "Jane Doe", "headline": "Engineer"}, {"career_timeline": []}, [], []
    )
    assert brief.prospect_name == "Jane Doe"
    assert metadata["synthesis_method"] == "rule_based"
    assert metadata["provider"] is None


def test_rule_based_synthesis_with_empty_inputs_produces_valid_brief_with_research_gaps():
    """Review Focus #2 (rule-based path): empty career/activity/sources must
    degrade to [] plus research_gaps entries, never raise and never
    fabricate placeholder content."""
    brief, _ = rule_based_synthesis(None, {"career_timeline": []}, [], [])

    assert brief.career_timeline == []
    assert brief.activity == []
    assert brief.recurring_themes == []
    assert len(brief.research_gaps.missing_information) > 0
    assert brief.outreach_strategy.angle is None
    assert brief.outreach_strategy.primary_hooks == []


def test_rule_based_synthesis_career_timeline_survives_citation_validator_round_trip():
    """Preflight-flagged soft risk: career_timeline/activity entries built
    by rule_based_synthesis must carry source_ids that resolve to real
    entries in the sources list it returns, so validate_brief does not
    wipe them out."""
    career = {
        "career_timeline": [
            {
                "organization": "Acme",
                "title": "Senior Engineer",
                "start_date": "2020-01",
                "end_date": None,
                "description": None,
                "source_ids": ["profile"],
                "confidence": "medium",
            }
        ]
    }
    activity = [
        {
            "activity_type": "original_post",
            "topic": "AI",
            "summary": "Posted about AI",
            "url": "https://example.com/post",
            "published_at": None,
            "authored_by_person": True,
            "relevance": None,
            "confidence": "medium",
            "source_ids": [],
        }
    ]

    brief, _ = rule_based_synthesis(
        {"full_name": "Jane Doe", "linkedin_url": "https://linkedin.com/in/jane"}, career, activity, []
    )

    # rule_based_synthesis already runs validate_brief internally — assert
    # the entries survived that pass.
    assert len(brief.career_timeline) == 1
    assert brief.career_timeline[0].organization == "Acme"
    assert len(brief.activity) == 1
    assert brief.activity[0].topic == "AI"

    # Explicit round-trip through validate_brief again, per the brief's
    # instruction to verify this does not wipe career_timeline/activity.
    revalidated = validate_brief(brief)
    assert len(revalidated.career_timeline) == 1
    assert len(revalidated.activity) == 1

    known_ids = {s.id for s in brief.sources}
    assert "profile" in known_ids
    assert all(sid in known_ids for sid in brief.activity[0].source_ids)


def test_rule_based_synthesis_folds_company_gaps_into_missing_information():
    brief, _ = rule_based_synthesis(
        {"full_name": "Jane Doe"},
        {"career_timeline": []},
        [],
        [],
        ["Could not confidently identify Acme Robotics's official website"],
    )

    assert (
        "Could not confidently identify Acme Robotics's official website"
        in brief.research_gaps.missing_information
    )
