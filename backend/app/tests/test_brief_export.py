import io
import json

import pdfplumber

from app.services.brief_export import to_json, to_markdown, to_pdf

SAMPLE_BRIEF = {
    "prospect_name": "Jane Doe",
    "snapshot": [{"text": "Senior Engineer at Acme", "is_inference": True, "confidence": "high"}],
    "current_role": [],
    "company_overview": [
        {"text": "Acme is a robotics company", "is_inference": False, "confidence": "medium", "source_ids": ["s1"]}
    ],
    "career_timeline": [
        {
            "organization": "Acme",
            "title": "Senior Engineer",
            "start_date": "2020-01",
            "end_date": None,
            "description": "Led the platform team",
            "source_ids": ["profile"],
            "confidence": "medium",
        }
    ],
    "expertise": [],
    "activity": [
        {
            "activity_type": "interview_or_podcast",
            "topic": "AI infrastructure",
            "summary": "Talked about AI infra on a podcast",
            "url": "https://example.com/podcast",
            "published_at": "2026-02-01",
            "authored_by_person": True,
            "relevance": None,
            "confidence": "medium",
            "source_ids": ["s0"],
        }
    ],
    "recurring_themes": [],
    "company_context": [
        {
            "text": "Acme announced a Series B",
            "is_inference": False,
            "confidence": "high",
            "source_ids": ["s1"],
            "date": "2026-01-15",
        }
    ],
    "communication_style": [],
    "likely_priorities": [],
    "personalization_hooks": [
        {
            "evidence": "Mentioned in a conference talk",
            "relevance": "Shows thought leadership",
            "outreach_angle": "Ask about the talk",
            "source_ids": ["s0"],
            "confidence": "medium",
        }
    ],
    "outreach_strategy": {
        "angle": "Lead with the podcast appearance",
        "primary_hooks": ["The podcast interview"],
        "question_or_value_prop": "How are you scaling AI infra?",
        "opening_approach": "Reference the podcast",
        "avoid": ["Don't mention competitors"],
    },
    "sources": [
        {"id": "s0", "url": "https://example.com/talk", "title": "Conference Talk"},
        {"id": "s1", "url": "https://example.com/news", "title": "Acme Series B announcement"},
    ],
    "research_gaps": {
        "missing_information": ["No company overview could be derived without AI synthesis"],
        "limited_coverage_areas": [],
        "conflicting_information": [],
        "unverified_claims": [],
        "inaccessible_sources": [],
    },
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


def test_markdown_export_renders_career_timeline():
    md = to_markdown(SAMPLE_BRIEF)
    assert "## Career Timeline" in md
    assert "Senior Engineer" in md
    assert "Acme" in md
    assert "2020-01" in md
    assert "Led the platform team" in md


def test_markdown_export_renders_activity_with_type_date_and_url():
    md = to_markdown(SAMPLE_BRIEF)
    assert "## Activity" in md
    assert "interview or podcast" in md
    assert "AI infrastructure" in md
    assert "2026-02-01" in md
    assert "https://example.com/podcast" in md


def test_markdown_export_renders_personalization_hooks_with_evidence_and_angle():
    md = to_markdown(SAMPLE_BRIEF)
    assert "## Personalisation Hooks" in md
    assert "Evidence: Mentioned in a conference talk" in md
    assert "Relevance: Shows thought leadership" in md
    assert "Outreach angle: Ask about the talk" in md


def test_markdown_export_renders_outreach_strategy():
    md = to_markdown(SAMPLE_BRIEF)
    assert "## Outreach Strategy" in md
    assert "Lead with the podcast appearance" in md
    assert "How are you scaling AI infra?" in md
    assert "Reference the podcast" in md
    assert "Don't mention competitors" in md


def test_markdown_export_renders_research_gaps():
    md = to_markdown(SAMPLE_BRIEF)
    assert "## Research Gaps" in md
    assert "No company overview could be derived without AI synthesis" in md


def test_markdown_export_renders_company_context_claim_with_date():
    md = to_markdown(SAMPLE_BRIEF)
    assert "Acme announced a Series B" in md
    assert "2026-01-15" in md


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


def test_pdf_export_includes_career_timeline_activity_and_outreach_strategy():
    pdf_bytes = to_pdf(SAMPLE_BRIEF)
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    assert "Career Timeline" in text
    assert "Activity" in text
    assert "Outreach Strategy" in text
    assert "Research Gaps" in text


def test_markdown_export_omits_empty_sections():
    md = to_markdown(SAMPLE_BRIEF)
    assert "## Current Role" not in md
    assert "## Expertise" not in md
