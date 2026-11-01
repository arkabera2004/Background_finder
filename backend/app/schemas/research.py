import re

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
