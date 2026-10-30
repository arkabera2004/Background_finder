import json
from pathlib import Path

import jsonschema
import pytest

from app.schemas.brief import ProspectBrief

SCHEMA_PATH = Path(__file__).resolve().parent.parent.parent.parent / "docs" / "brief-schema.json"


@pytest.fixture
def schema():
    return json.loads(SCHEMA_PATH.read_text())


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
    )
    jsonschema.validate(instance=brief.model_dump(), schema=schema)


def test_schema_rejects_missing_required_field(schema):
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance={"snapshot": []}, schema=schema)


def test_schema_rejects_wrong_type_for_confidence(schema):
    invalid = {
        "prospect_name": "Jane Doe",
        "snapshot": [{"text": "x", "confidence": "super-high"}],
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=invalid, schema=schema)
