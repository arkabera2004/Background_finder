"""Regenerates docs/brief-schema.json directly from app.schemas.brief.ProspectBrief
so the canonical schema can never drift from the actual validated model.

Run: PYTHONPATH=. .venv/bin/python scripts/generate_brief_schema.py
"""

import json
from pathlib import Path

from app.schemas.brief import ProspectBrief

OUTPUT_PATH = Path(__file__).resolve().parent.parent.parent / "docs" / "brief-schema.json"


def main() -> None:
    schema = ProspectBrief.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = "https://github.com/arkabera2004/Background_finder/docs/brief-schema.json"
    OUTPUT_PATH.write_text(json.dumps(schema, indent=2) + "\n")
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
