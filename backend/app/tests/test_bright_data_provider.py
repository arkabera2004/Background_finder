import pytest

from app.providers.bright_data_provider import BrightDataProvider
from app.providers.profile_provider import ProviderUnavailableError


def test_parses_experience_and_education_from_fixture_record():
    """Deterministic fixture, not a live Bright Data response — see the
    caveat comments in bright_data_provider.py's _parse_experiences/
    _parse_education: the exact field names have not been confirmed live."""
    provider = BrightDataProvider(api_key="test-key")
    record = {
        "name": "Jordan Avery",
        "position": "Senior Product Manager",
        "current_company": {"name": "Acme Robotics", "title": "Senior Product Manager"},
        "experience": [
            {
                "title": "Senior Product Manager",
                "company": "Acme Robotics",
                "start_date": "2021-06",
                "end_date": None,
                "description": "Leads the robotics product line.",
            },
            {
                "title": "Product Manager",
                "company": "Globex Corp",
                "start_date": "2018-01",
                "end_date": "2021-05",
            },
        ],
        "education": [
            {
                "title": "State University",
                "degree": "B.S.",
                "field": "Computer Science",
                "start_year": 2012,
                "end_year": 2016,
            }
        ],
    }

    person = provider._parse(records=[record], linkedin_url="https://linkedin.com/in/jordan-avery")

    assert person.full_name == "Jordan Avery"
    assert person.current_company == "Acme Robotics"
    assert len(person.experiences) == 2
    assert person.experiences[0].company == "Acme Robotics"
    assert person.experiences[1].end_date == "2021-05"
    assert len(person.education) == 1
    assert person.education[0].institution == "State University"
    assert person.education[0].start_date == "2012"


def test_parse_skips_malformed_experience_and_education_entries():
    provider = BrightDataProvider(api_key="test-key")
    record = {
        "name": "Jane Doe",
        "experience": [{"title": "Missing company field"}, "not-a-dict"],
        "education": [{"degree": "Missing institution field"}],
    }

    person = provider._parse(records=[record], linkedin_url="https://linkedin.com/in/jane-doe")

    assert person.experiences == []
    assert person.education == []


def test_parse_raises_without_name():
    provider = BrightDataProvider(api_key="test-key")
    with pytest.raises(ProviderUnavailableError):
        provider._parse(records=[{}], linkedin_url="https://linkedin.com/in/nobody")
