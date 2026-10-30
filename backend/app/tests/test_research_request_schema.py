import pytest
from pydantic import ValidationError

from app.schemas.research_request import ResearchRequest


def test_accepts_linkedin_url_only():
    req = ResearchRequest(linkedin_url="https://linkedin.com/in/jane-doe")
    assert req.linkedin_url == "https://linkedin.com/in/jane-doe"


def test_accepts_name_and_company():
    req = ResearchRequest(full_name="Jane Doe", company="Acme")
    assert req.company == "Acme"


def test_accepts_name_and_pasted_text():
    req = ResearchRequest(full_name="Jane Doe", pasted_text="x" * 60)
    assert req.pasted_text is not None


def test_rejects_no_intake_method():
    with pytest.raises(ValidationError, match="Provide exactly one intake method"):
        ResearchRequest()


def test_rejects_pasted_text_without_name():
    with pytest.raises(ValidationError, match="full_name is required"):
        ResearchRequest(pasted_text="x" * 60)


def test_rejects_invalid_depth():
    with pytest.raises(ValidationError, match="depth must be one of"):
        ResearchRequest(full_name="Jane Doe", company="Acme", depth="extreme")
