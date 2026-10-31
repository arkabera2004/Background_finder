from app.schemas.brief import (
    ActivityItem,
    ActivityType,
    CareerEntry,
    Claim,
    OutreachStrategy,
    PersonalizationHook,
    ProspectBrief,
    Source,
)
from app.services.citation_validator import has_enough_hooks, validate_brief

MIN_HOOKS = 3


def _outreach() -> OutreachStrategy:
    return OutreachStrategy(angle="test angle")


def _brief(**kwargs) -> ProspectBrief:
    kwargs.setdefault("outreach_strategy", _outreach())
    return ProspectBrief(prospect_name="Jane Doe", **kwargs)


def test_drops_unsourced_factual_claim():
    brief = _brief(
        sources=[Source(id="s1", url="https://example.com")],
        snapshot=[Claim(text="Works at Acme", source_ids=["s1"]), Claim(text="Made up fact")],
    )
    cleaned = validate_brief(brief)
    assert len(cleaned.snapshot) == 1
    assert cleaned.snapshot[0].text == "Works at Acme"


def test_keeps_inference_without_source():
    brief = _brief(
        likely_priorities=[Claim(text="Likely cares about growth", is_inference=True)]
    )
    cleaned = validate_brief(brief)
    assert len(cleaned.likely_priorities) == 1


def test_drops_claim_with_unknown_source_id():
    brief = _brief(snapshot=[Claim(text="X", source_ids=["nonexistent"])])
    cleaned = validate_brief(brief)
    assert len(cleaned.snapshot) == 0


def test_drops_hook_without_valid_source():
    brief = _brief(
        sources=[Source(id="s1", url="https://example.com")],
        personalization_hooks=[
            PersonalizationHook(
                evidence="Good hook",
                relevance="r",
                outreach_angle="a",
                source_ids=["s1"],
            ),
            PersonalizationHook(
                evidence="Bad hook",
                relevance="r",
                outreach_angle="a",
                source_ids=["missing"],
            ),
        ],
    )
    cleaned = validate_brief(brief)
    assert len(cleaned.personalization_hooks) == 1
    assert cleaned.personalization_hooks[0].evidence == "Good hook"


def test_has_enough_hooks():
    brief = _brief(
        sources=[Source(id="s1", url="https://example.com")],
        personalization_hooks=[
            PersonalizationHook(
                evidence=f"h{i}", relevance="r", outreach_angle="a", source_ids=["s1"]
            )
            for i in range(3)
        ],
    )
    assert has_enough_hooks(brief) is True
    assert has_enough_hooks(_brief()) is False


def test_drops_career_entry_with_fabricated_source():
    brief = _brief(
        sources=[Source(id="s1", url="https://example.com")],
        career_timeline=[
            CareerEntry(
                organization="Acme",
                title="Engineer",
                source_ids=["s1"],
            ),
            CareerEntry(
                organization="FakeCo",
                title="Fake Title",
                source_ids=["fake"],
            ),
        ],
    )
    cleaned = validate_brief(brief)
    assert len(cleaned.career_timeline) == 1
    assert cleaned.career_timeline[0].organization == "Acme"
    assert cleaned.career_timeline[0].source_ids == ["s1"]


def test_keeps_career_entry_with_mixed_valid_and_invalid_sources():
    brief = _brief(
        sources=[Source(id="s1", url="https://example.com")],
        career_timeline=[
            CareerEntry(
                organization="Acme",
                title="Engineer",
                source_ids=["s1", "fake"],
            ),
        ],
    )
    cleaned = validate_brief(brief)
    assert len(cleaned.career_timeline) == 1
    assert cleaned.career_timeline[0].source_ids == ["s1"]


def test_drops_activity_item_with_no_valid_sources():
    brief = _brief(
        sources=[Source(id="s1", url="https://example.com")],
        activity=[
            ActivityItem(
                activity_type=ActivityType.ORIGINAL_POST,
                topic="AI",
                summary="Posted about AI",
                url="https://example.com/post",
                source_ids=["s1"],
            ),
            ActivityItem(
                activity_type=ActivityType.ORIGINAL_POST,
                topic="Fabricated",
                summary="Fabricated post",
                url="https://example.com/fake",
                source_ids=["fake"],
            ),
        ],
    )
    cleaned = validate_brief(brief)
    assert len(cleaned.activity) == 1
    assert cleaned.activity[0].topic == "AI"


def test_claim_with_inference_survives_in_company_context():
    brief = _brief(
        company_context=[
            Claim(text="Likely scaling up", is_inference=True),
            Claim(text="Fabricated detail", source_ids=["fake"]),
        ]
    )
    cleaned = validate_brief(brief)
    assert len(cleaned.company_context) == 1
    assert cleaned.company_context[0].text == "Likely scaling up"
