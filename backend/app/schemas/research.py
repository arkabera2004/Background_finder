import re

from pydantic import BaseModel, field_validator

LINKEDIN_PROFILE_RE = re.compile(
    r"^https?://(?:[a-z]{2,3}\.)?linkedin\.com/in/[A-Za-z0-9\-_%]+/?(?:\?.*)?$",
    re.IGNORECASE,
)
LINKEDIN_COMPANY_RE = re.compile(
    r"^https?://(?:[a-z]{2,3}\.)?linkedin\.com/company/", re.IGNORECASE
)


class InvalidLinkedInUrlError(ValueError):
    pass


def normalize_linkedin_profile_url(raw: str) -> str:
    """Validate and normalize a LinkedIn profile URL.

    Rejects company URLs and anything that isn't a /in/ profile.
    """
    candidate = raw.strip()
    if LINKEDIN_COMPANY_RE.match(candidate):
        raise InvalidLinkedInUrlError(
            "This is a LinkedIn company page, not a personal profile. "
            "Provide a URL like https://linkedin.com/in/username."
        )
    if not LINKEDIN_PROFILE_RE.match(candidate):
        raise InvalidLinkedInUrlError(
            "Not a valid LinkedIn profile URL. Expected format: "
            "https://linkedin.com/in/username."
        )
    # Strip query params and trailing slash for a canonical form.
    without_query = candidate.split("?")[0].rstrip("/")
    return without_query


class ResearchByUrl(BaseModel):
    linkedin_url: str
    depth: str = "standard"

    @field_validator("linkedin_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        return normalize_linkedin_profile_url(v)

    @field_validator("depth")
    @classmethod
    def validate_depth(cls, v: str) -> str:
        if v not in ("quick", "standard", "deep"):
            raise ValueError("depth must be one of: quick, standard, deep")
        return v


class ResearchByNameCompany(BaseModel):
    full_name: str
    company: str
    depth: str = "standard"

    @field_validator("full_name", "company")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be blank")
        return v.strip()

    @field_validator("depth")
    @classmethod
    def validate_depth(cls, v: str) -> str:
        if v not in ("quick", "standard", "deep"):
            raise ValueError("depth must be one of: quick, standard, deep")
        return v


class ResearchByPastedText(BaseModel):
    full_name: str
    pasted_text: str
    depth: str = "standard"

    @field_validator("pasted_text")
    @classmethod
    def min_length(cls, v: str) -> str:
        if len(v.strip()) < 50:
            raise ValueError("pasted_text must be at least 50 characters")
        return v
