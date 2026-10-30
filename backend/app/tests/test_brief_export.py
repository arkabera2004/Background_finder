import io
import json

import pdfplumber

from app.services.brief_export import to_json, to_markdown, to_pdf

SAMPLE_BRIEF = {
    "prospect_name": "Jane Doe",
    "snapshot": [{"text": "Senior Engineer at Acme", "is_inference": True, "confidence": "high"}],
    "career_story": [],
    "current_role": [],
    "company": [],
    "content_and_interests": [],
    "communication_style": [],
    "likely_priorities": [],
    "hooks": [{"text": "Mentioned in a conference talk", "source_ids": ["s0"]}],
    "dos_and_donts": [],
    "sources": [{"id": "s0", "url": "https://example.com/talk", "title": "Conference Talk"}],
}


def test_json_export_round_trips():
    exported = to_json(SAMPLE_BRIEF)
    assert json.loads(exported) == SAMPLE_BRIEF


def test_markdown_export_contains_all_sections():
    md = to_markdown(SAMPLE_BRIEF)
    assert "# Prospect Brief: Jane Doe" in md
    assert "Senior Engineer at Acme" in md
    assert "_(inference)_" in md
    assert "Mentioned in a conference talk" in md
    assert "https://example.com/talk" in md


def test_pdf_export_produces_valid_readable_pdf():
    """Real round-trip: generate with ReportLab, read back with pdfplumber
    (a different library), and verify the actual text content — not just
    that bytes were produced."""
    pdf_bytes = to_pdf(SAMPLE_BRIEF)
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    assert "Jane Doe" in text
    assert "Senior Engineer at Acme" in text
    assert "example.com/talk" in text


def test_markdown_export_omits_empty_sections():
    md = to_markdown(SAMPLE_BRIEF)
    assert "## Career Story" not in md
    assert "## Company" not in md
