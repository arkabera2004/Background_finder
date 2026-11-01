"""Unified identity attribution: decide whether a piece of text is about the
research subject, a different person with the same name, or can't be
determined either way.

Built in response to a live audit (Vineet Shukla run) that found two
compounding defects: (1) the identity fingerprint used to corroborate a
match was built from the current employer only, so a stale/thin profile
snapshot caused the subject's own press coverage to be rejected as a
namesake; and (2) only one of two search-derived channels actually ran the
namesake check, so the same kind of story that got rejected via one path
sailed through unfiltered via the other, attributing a different person's
interview to the subject.

The fix here is a single scorer, used by every channel that turns a search
result into either brief.activity or brief.sources, with three outcomes
instead of two:
  - "subject": positively corroborated (matches an employer, title, school,
    or the profile slug) and not simultaneously conflicting with a known
    different person's employer.
  - "namesake": the text matches an employer/context we've already
    confirmed belongs to a *different* person sharing this name (from an
    earlier item in the same run) — a hard reject.
  - "unverified": mentions the subject's name but has neither a positive
    corroboration nor a known conflict. Absence of corroboration is not
    evidence of a different person — these are excluded from the brief
    rather than guessed into either bucket.
  - "drop": doesn't even mention the name. Not evidence about anyone in
    particular; discarded outright (this is what keeps unrelated directory/
    aggregator pages out of the source list).
"""

import re
from dataclasses import dataclass, field

_WORD_RE = re.compile(r"[a-z0-9]+")

# Common job-title/business words that appear across unrelated roles and
# companies — a match on only these is not real corroboration (e.g. "head"
# in "Business Head" vs. "Head of Data" is a coincidence, not evidence).
_GENERIC_FINGERPRINT_WORDS = {
    "head", "senior", "junior", "director", "manager", "president", "chief",
    "vice", "global", "data", "science", "sciences", "technology",
    "technologies", "business", "group", "solutions", "systems", "services",
    "international", "corporation", "company", "officer", "lead", "team",
    "digital", "engineering", "product", "products", "management",
}


@dataclass
class IdentityFingerprint:
    name: str
    profile_slug: str | None = None
    employers: set[str] = field(default_factory=set)
    titles: set[str] = field(default_factory=set)
    schools: set[str] = field(default_factory=set)
    location: str | None = None
    # Populated progressively within a run as other items are confirmed to
    # belong to a different, same-named person — a later item mentioning
    # one of these employers is a hard-reject even if it also happens to
    # share a generic token with the subject.
    known_other_employers: set[str] = field(default_factory=set)

    def fingerprint_tokens(self) -> set[str]:
        tokens: set[str] = set()
        for value in (*self.employers, *self.titles, *self.schools):
            tokens |= _tokens(value)
        if self.profile_slug:
            tokens |= _tokens(self.profile_slug)
        if self.location:
            tokens |= _tokens(self.location)
        # Single common words (e.g. "data", "senior") are too weak alone to
        # count as corroboration — require a distinctive token, long enough
        # and not a generic job-title/business word.
        return {t for t in tokens if len(t) >= 4 and t not in _GENERIC_FINGERPRINT_WORDS}


def _tokens(text: str) -> set[str]:
    return set(_WORD_RE.findall(text.lower()))


def _slug_from_linkedin_url(url: str | None) -> str | None:
    if not url:
        return None
    match = re.search(r"linkedin\.com/in/([a-zA-Z0-9\-_%]+)", url)
    return match.group(1).replace("-", " ") if match else None


def build_fingerprint(
    full_name: str,
    linkedin_url: str | None,
    current_company: str | None,
    headline: str | None,
    experiences: list,
    education: list,
    location: str | None = None,
) -> IdentityFingerprint:
    employers: set[str] = set()
    if current_company:
        employers.add(current_company)
    for exp in experiences or []:
        company = getattr(exp, "company", None)
        if company:
            employers.add(company)

    titles: set[str] = set()
    if headline:
        titles.add(headline)
    for exp in experiences or []:
        title = getattr(exp, "title", None)
        if title:
            titles.add(title)

    schools: set[str] = set()
    for edu in education or []:
        institution = getattr(edu, "institution", None)
        if institution:
            schools.add(institution)

    return IdentityFingerprint(
        name=full_name,
        profile_slug=_slug_from_linkedin_url(linkedin_url),
        employers=employers,
        titles=titles,
        schools=schools,
        location=location,
    )


def score_item(text: str, fp: IdentityFingerprint) -> tuple[str, int]:
    """Returns (verdict, score). verdict is one of subject/namesake/
    unverified/drop. score is the number of positive fingerprint matches
    (0 for namesake/drop)."""
    if not text:
        return "drop", 0
    lowered = text.lower()

    if fp.name.lower() not in lowered:
        return "drop", 0

    item_tokens = _tokens(text)
    # A conflict is only meaningful if it's a *distinctive* employer token,
    # not an accidental generic-word overlap.
    has_conflict = any(
        other
        and {t for t in _tokens(other) if len(t) >= 4 and t not in _GENERIC_FINGERPRINT_WORDS}
        & item_tokens
        for other in fp.known_other_employers
    )

    hits = len(fp.fingerprint_tokens() & item_tokens)

    if has_conflict and hits == 0:
        return "namesake", -1
    if hits >= 1:
        return "subject", hits
    return "unverified", 0


def canonical_url(url: str) -> str:
    """Normalizes a URL for dedup: strips scheme variance (http/https),
    the "www."/"in." www-style subdomain, trailing slash, and query string,
    so the same page reached two different ways collapses to one entry."""
    cleaned = re.sub(r"^https?://", "", url.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"^(www|in)\.", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.split("?")[0].split("#")[0]
    cleaned = cleaned.rstrip("/")
    return cleaned.lower()


def normalized_title(title: str | None) -> str:
    if not title:
        return ""
    return " ".join(_tokens(title))
