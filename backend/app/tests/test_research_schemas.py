import pytest
from pydantic import ValidationError

from app.schemas.research import (
    InvalidLinkedInUrlError,
    ResearchByNameCompany,
    ResearchByPastedText,
    ResearchByUrl,
    normalize_linkedin_profile_url,
)


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://linkedin.com/in/jane-doe", "https://linkedin.com/in/jane-doe"),
        ("https://www.linkedin.com/in/jane-doe/", "https://www.linkedin.com/in/jane-doe"),
        (
            "https://linkedin.com/in/jane-doe?trk=abc",
            "https://linkedin.com/in/jane-doe",
        ),
    ],
)
def test_normalizes_valid_profile_urls(url, expected):
    assert normalize_linkedin_profile_url(url) == expected


def test_rejects_company_url():
    with pytest.raises(InvalidLinkedInUrlError, match="company page"):
        normalize_linkedin_profile_url("https://linkedin.com/company/acme")


@pytest.mark.parametrize(
    "bad_url",
    [
        "https://example.com/in/jane-doe",
        "not a url",
        "https://linkedin.com/jobs/view/123",
    ],
)
def test_rejects_malformed_urls(bad_url):
    with pytest.raises(InvalidLinkedInUrlError):
        normalize_linkedin_profile_url(bad_url)


def test_research_by_url_rejects_bad_depth():
    with pytest.raises(ValidationError):
        ResearchByUrl(linkedin_url="https://linkedin.com/in/jane-doe", depth="extreme")


def test_research_by_name_company_rejects_blank():
    with pytest.raises(ValidationError):
        ResearchByNameCompany(full_name="  ", company="Acme")


def test_research_by_pasted_text_rejects_too_short():
    with pytest.raises(ValidationError):
        ResearchByPastedText(full_name="Jane Doe", pasted_text="too short")
