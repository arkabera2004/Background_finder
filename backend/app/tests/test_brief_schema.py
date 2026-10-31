import json
from pathlib import Path

import jsonschema
import pytest
from pydantic import ValidationError

from app.schemas.brief import (
    ActivityItem,
    CareerEntry,
    OutreachStrategy,
    PersonalizationHook,
    ProspectBrief,
    ResearchGaps,
    Source,
)

SCHEMA_PATH = Path(__file__).resolve().parent.parent.parent.parent / "docs" / "brief-schema.json"

NEW_FIELDS = {
    "prospect_name",
    "snapshot",
    "current_role",
    "company_overview",
    "career_timeline",
    "expertise",
    "activity",
    "recurring_themes",
    "company_context",
    "communication_style",
    "likely_priorities",
    "personalization_hooks",
    "outreach_strategy",
    "sources",
    "research_gaps",
}

DROPPED_FIELDS = {"career_story", "content_and_interests", "hooks", "dos_and_donts", "company"}


@pytest.fixture
def schema():
    return json.loads(SCHEMA_PATH.read_text())


def test_prospect_brief_has_all_new_fields_and_none_of_the_dropped_ones():
    field_names = set(ProspectBrief.model_fields.keys())
    assert NEW_FIELDS <= field_names
    assert field_names & DROPPED_FIELDS == set()


def test_career_entry_round_trips():
    entry = CareerEntry(
        organization="Acme Corp",
        title="VP Engineering",
        start_date="2020-01",
        end_date=None,
        description="Led platform team",
        source_ids=["s1"],
    )
    round_tripped = CareerEntry.model_validate(entry.model_dump())
    assert round_tripped == entry


def test_activity_item_round_trips():
    item = ActivityItem(
        activity_type="original_post",
        topic="AI in healthcare",
        summary="Posted about AI adoption",
        url="https://example.com/post/1",
        published_at="2026-01-01",
        source_ids=["s1"],
    )
    round_tripped = ActivityItem.model_validate(item.model_dump())
    assert round_tripped == item


def test_personalization_hook_round_trips():
    hook = PersonalizationHook(
        evidence="Posted about scaling infra",
        relevance="Shows infra pain point",
        outreach_angle="Mention infra scaling experience",
        source_ids=["s1"],
    )
    round_tripped = PersonalizationHook.model_validate(hook.model_dump())
    assert round_tripped == hook


def test_outreach_strategy_round_trips():
    strategy = OutreachStrategy(
        angle="Focus on infra scaling pain",
        primary_hooks=["Posted about scaling infra"],
        question_or_value_prop="Can help reduce infra costs",
        opening_approach="Reference recent post",
        avoid=["Don't mention competitor by name"],
    )
    round_tripped = OutreachStrategy.model_validate(strategy.model_dump())
    assert round_tripped == strategy


def test_research_gaps_round_trips():
    gaps = ResearchGaps(
        missing_information=["No recent activity found"],
        limited_coverage_areas=["Education history"],
        conflicting_information=[],
        unverified_claims=["Possible title change"],
        inaccessible_sources=["Private LinkedIn post"],
    )
    round_tripped = ResearchGaps.model_validate(gaps.model_dump())
    assert round_tripped == gaps


def test_source_accepts_valid_source_type():
    source = Source(id="s1", url="https://example.com", source_type="company_news")
    assert source.source_type == "company_news"


def test_source_rejects_invalid_source_type():
    with pytest.raises(ValidationError):
        Source(id="s1", url="https://example.com", source_type="not_a_real_type")


def test_schema_file_matches_current_pydantic_model(schema):
    """If this fails, someone changed ProspectBrief without regenerating
    docs/brief-schema.json — run scripts/generate_brief_schema.py."""
    current = ProspectBrief.model_json_schema()
    current["$schema"] = schema["$schema"]
    current["$id"] = schema["$id"]
    assert schema == current


def test_schema_validates_a_real_brief(schema):
    brief = ProspectBrief(
        prospect_name="Jane Doe",
        snapshot=[{"text": "Senior Engineer", "is_inference": True}],
        outreach_strategy={"angle": "x"},
    )
    jsonschema.validate(instance=brief.model_dump(), schema=schema)


def test_schema_rejects_missing_required_field(schema):
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance={"snapshot": []}, schema=schema)


def test_schema_rejects_wrong_type_for_confidence(schema):
    invalid = {
        "prospect_name": "Jane Doe",
        "snapshot": [{"text": "x", "confidence": "super-high"}],
        "outreach_strategy": {"angle": "x"},
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=invalid, schema=schema)
