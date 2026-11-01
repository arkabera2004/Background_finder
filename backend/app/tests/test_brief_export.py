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
    assert "## Complete Career Timeline" in md
    assert "Senior Engineer" in md
    assert "Acme" in md
    assert "2020-01" in md
    assert "Led the platform team" in md


def test_markdown_export_renders_activity_with_type_date_and_url():
    md = to_markdown(SAMPLE_BRIEF)
    assert "## Posts, Reposts & Public Activity" in md
    assert "interview or podcast" in md
    assert "AI infrastructure" in md
    assert "2026-02-01" in md
    assert "https://example.com/podcast" in md


def test_markdown_export_renders_personalization_hooks_with_evidence_and_angle():
    md = to_markdown(SAMPLE_BRIEF)
    assert "## Common Ground & Conversation Opportunities" in md
    assert "Evidence: Mentioned in a conference talk" in md
    assert "Relevance: Shows thought leadership" in md
    assert "Outreach angle: Ask about the talk" in md


def test_markdown_export_renders_outreach_strategy():
    md = to_markdown(SAMPLE_BRIEF)
    assert "## Personalized Outreach Brief" in md
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
    assert "Personalized Outreach Brief" in text
    assert "Research Gaps" in text


def test_markdown_export_omits_empty_sections():
    md = to_markdown(SAMPLE_BRIEF)
    assert "## Current Role" not in md
    assert "## Expertise" not in md


DEEP_RESEARCH_BRIEF = {
    **SAMPLE_BRIEF,
    "identity_verification": {
        "profile_url": "https://linkedin.com/in/jane-doe",
        "matched_identifiers": ["Name: Jane Doe", "Current employer: Acme"],
        "confidence": "high",
        "limitations": "Anchored to a direct LinkedIn URL.",
    },
    "detailed_summary": [
        {"text": "Jane Doe has worked in robotics since 2020.", "is_inference": False, "source_ids": ["profile"]}
    ],
    "education": [
        {
            "institution": "State University",
            "degree": "B.S.",
            "field": "Computer Science",
            "start_date": "2012",
            "end_date": "2016",
            "date_precision": "approximate",
            "source_ids": ["profile"],
        }
    ],
    "company_profiles": [
        {
            "name": "Acme",
            "website": "https://acme.example",
            "what_they_do": "Builds robots",
            "person_role": "Senior Engineer",
            "start_date": "2020-01",
            "end_date": None,
            "date_precision": "exact",
            "source_ids": ["profile"],
            "uncertainty_note": None,
        }
    ],
    "achievements": [
        {"text": "Promoted to Senior Engineer in 2022", "is_inference": False, "source_ids": ["profile"]}
    ],
    "same_name_people": [
        {
            "name": "Jane Doe",
            "identity_summary": "CEO of a different company",
            "distinguishing_info": "Works in retail, not robotics",
            "source_ids": ["s0"],
            "why_confusable": "Shares the same full name",
            "why_different": "Does not mention Acme",
        }
    ],
    "related_personalities": [
        {
            "name": "John Smith",
            "role": "Co-founder",
            "connection_type": "colleague",
            "strength": "possible",
            "evidence": "Mentioned together in a conference recap",
            "source_ids": ["s0"],
        }
    ],
}


def test_markdown_export_renders_deep_research_sections_in_order():
    md = to_markdown(DEEP_RESEARCH_BRIEF)
    for heading in [
        "## Identity Verification",
        "## Executive Overview",
        "## Detailed Person Summary",
        "## Education & Early Background",
        "## Complete Career Timeline",
        "## Company-by-Company Overview",
        "## Achievements & Milestones",
        "## Posts, Reposts & Public Activity",
        "## Publications, Talks & Interviews",
        "## People with the Same Name",
        "## Related Personalities",
    ]:
        assert heading in md, heading

    order = [md.index(h) for h in ["## Identity Verification", "## Executive Overview", "## Education & Early Background", "## Complete Career Timeline"]]
    assert order == sorted(order)

    assert "https://linkedin.com/in/jane-doe" in md
    assert "State University" in md
    assert "acme.example" in md
    assert "CEO of a different company" in md
    assert "John Smith" in md


def test_pdf_export_renders_deep_research_sections():
    pdf_bytes = to_pdf(DEEP_RESEARCH_BRIEF)
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    assert "Identity Verification" in text
    assert "Education & Early Background" in text
    assert "Company-by-Company Overview" in text
    assert "Achievements & Milestones" in text
    assert "People with the Same Name" in text
    assert "Related Personalities" in text
