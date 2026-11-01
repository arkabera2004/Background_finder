"""Deterministic, post-synthesis enrichment of a ProspectBrief.

These sections are built the same way regardless of whether the brief came
from the AI path or the rule-based fallback — none of them need prose
generation, just honest structuring of data the pipeline already collected
(or an explicit statement that it's not available). Keeping them out of the
AI prompt also avoids the model inventing names for sections that are
expected to often be empty.
"""

import re

from app.schemas.brief import (
    Claim,
    CompanyProfile,
    Confidence,
    ConnectionStrength,
    DatePrecision,
    EducationEntry,
    IdentityVerification,
    ProspectBrief,
    RelatedPersonality,
    SameNameMatch,
    Source,
)
from app.services.citation_validator import validate_brief

_NAME_PATTERN = re.compile(r"\b([A-Z][a-z]+(?:\s[A-Z][a-z]+){1,2})\b")

# Deterministic education fallback (F7): when the profile provider gives no
# structured education (e.g. a thin/partial scrape, or pasted text), scan
# whatever source text the pipeline already collected for well-known
# institution name patterns rather than reporting "not found" when the
# press coverage already in hand plainly states it.
_INSTITUTION_PATTERNS = [
    re.compile(r"\b(IIM|IIT|NIT)\s+([A-Z][a-zA-Z]+)\b"),
    re.compile(r"\bMNNIT(?:\s+Allahabad)?\b"),
    re.compile(r"\bBITS\s+Pilani\b"),
    re.compile(
        r"\b([A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+){0,3}\s"
        r"(?:University|Institute of Technology|College of Engineering))\b"
    ),
]
_DEGREE_PATTERN = re.compile(r"\b(MBA|B\.?Tech\.?|M\.?Tech\.?|PhD|B\.?E\.?|M\.?S\.?|MCA|BCA)\b")
_STOPWORD_STARTS = {
    "The",
    "This",
    "That",
    "These",
    "Those",
    "A",
    "An",
    "In",
    "On",
    "At",
    "For",
    "With",
    "From",
    "We",
    "I",
    "He",
    "She",
    "They",
}
MAX_RELATED_PERSONALITIES = 5


def build_identity_verification(
    person_data: dict | None, linkedin_url: str | None
) -> IdentityVerification:
    matched: list[str] = []
    if person_data:
        if person_data.get("full_name"):
            matched.append(f"Name: {person_data['full_name']}")
        if person_data.get("current_company"):
            matched.append(f"Current employer: {person_data['current_company']}")
        if person_data.get("headline"):
            matched.append(f"Headline: {person_data['headline']}")

    if linkedin_url:
        confidence = Confidence.HIGH
        limitations = (
            "Identity anchored directly to the supplied LinkedIn profile URL; "
            "other sources were corroborated against this profile's known "
            "employer(s), not independently re-verified against a government ID "
            "or other authoritative source."
        )
    else:
        confidence = Confidence.MEDIUM
        limitations = (
            "Identity was not anchored to a direct LinkedIn profile URL (pasted "
            "text or name + company intake) — other sources were corroborated "
            "against the employer name(s) supplied, not against a verified "
            "LinkedIn profile, so there is more residual risk of conflating a "
            "same-named individual."
        )

    return IdentityVerification(
        profile_url=linkedin_url,
        matched_identifiers=matched,
        confidence=confidence,
        limitations=limitations,
    )


def extract_education_from_sources(sources: list[Source]) -> list[dict]:
    """Regex fallback over source titles/excerpts for well-known institution
    names, used only when the profile provider gave no structured education
    data. Each match is cited to the source it was found in and marked
    "approximate" precision since no dates are extracted this way."""
    seen: set[str] = set()
    records: list[dict] = []
    for s in sources:
        text = f"{s.title or ''} {s.excerpt or ''}"
        if not text.strip():
            continue
        for pattern in _INSTITUTION_PATTERNS:
            for match in pattern.finditer(text):
                institution = match.group(0).strip()
                key = institution.lower()
                if key in seen:
                    continue
                seen.add(key)
                degree_match = _DEGREE_PATTERN.search(text)
                records.append(
                    {
                        "institution": institution,
                        "degree": degree_match.group(0) if degree_match else None,
                        "source_id": s.id,
                    }
                )
    return records


def build_education_entries(
    education_records: list[dict],
    profile_source_id: str | None,
    fallback_sources: list[Source] | None = None,
) -> list[EducationEntry]:
    entries = []
    source_ids = [profile_source_id] if profile_source_id else []
    for rec in education_records:
        if not rec.get("institution"):
            continue
        entries.append(
            EducationEntry(
                institution=rec["institution"],
                degree=rec.get("degree"),
                field=rec.get("field"),
                start_date=rec.get("start_date"),
                end_date=rec.get("end_date"),
                date_precision=DatePrecision.APPROXIMATE
                if rec.get("start_date")
                else DatePrecision.UNKNOWN,
                source_ids=source_ids,
                confidence=Confidence.MEDIUM,
            )
        )

    if entries or not fallback_sources:
        return entries

    for rec in extract_education_from_sources(fallback_sources):
        entries.append(
            EducationEntry(
                institution=rec["institution"],
                degree=rec.get("degree"),
                date_precision=DatePrecision.UNKNOWN,
                source_ids=[rec["source_id"]] if rec.get("source_id") else [],
                confidence=Confidence.LOW,
            )
        )
    return entries


def build_company_profiles(
    brief: ProspectBrief, company_research: dict | None
) -> list[CompanyProfile]:
    researched_name = (company_research or {}).get("company")
    domain = (company_research or {}).get("domain_guess")

    profiles: list[CompanyProfile] = []
    seen: set[str] = set()
    for entry in brief.career_timeline:
        key = entry.organization.lower()
        if key in seen:
            continue
        seen.add(key)

        is_researched = researched_name is not None and key == researched_name.lower()
        profiles.append(
            CompanyProfile(
                name=entry.organization,
                website=f"https://{domain}" if is_researched and domain else None,
                what_they_do=None,
                person_role=entry.title,
                role_scope=entry.description,
                start_date=entry.start_date,
                end_date=entry.end_date,
                date_precision=entry.date_precision,
                source_ids=entry.source_ids,
                confidence=entry.confidence,
                uncertainty_note=None
                if is_researched
                else "Company itself was not independently researched beyond the "
                "person's stated role — no website/industry lookup performed for "
                "past employers.",
            )
        )
    return profiles


def build_detailed_summary(brief: ProspectBrief) -> list[Claim]:
    """A chronological narrative built from facts synthesis already
    produced, so it stays start-to-present without re-deriving anything."""
    if brief.detailed_summary:
        return brief.detailed_summary

    paragraphs: list[Claim] = []
    if brief.snapshot:
        paragraphs.extend(brief.snapshot)

    for entry in sorted(
        brief.career_timeline, key=lambda e: e.start_date or "", reverse=False
    ):
        span = f"{entry.start_date or 'unknown date'} to {entry.end_date or 'present'}"
        text = f"{span}: {entry.title} at {entry.organization}."
        if entry.description:
            text += f" {entry.description}"
        paragraphs.append(
            Claim(
                text=text,
                source_ids=entry.source_ids,
                confidence=entry.confidence,
                is_inference=False,
            )
        )

    if not paragraphs:
        paragraphs.append(
            Claim(
                text="Not enough corroborated information was gathered to build a "
                "start-to-present narrative for this person.",
                is_inference=True,
            )
        )
    return paragraphs


def build_same_name_people(
    same_name_candidates: list[dict], all_sources: list[Source]
) -> tuple[list[SameNameMatch], list[Source]]:
    known_ids = {s.id for s in all_sources}
    matches: list[SameNameMatch] = []
    new_sources = list(all_sources)
    for i, cand in enumerate(same_name_candidates):
        url = cand.get("url")
        if not url:
            continue
        source_id = f"namesake-{i}"
        if source_id not in known_ids:
            new_sources.append(Source(id=source_id, url=url, title=cand.get("identity_summary")))
            known_ids.add(source_id)
        matches.append(
            SameNameMatch(
                name=cand.get("name", "Unknown"),
                identity_summary=cand.get("identity_summary", "Unknown"),
                distinguishing_info=cand.get("distinguishing_info"),
                source_ids=[source_id],
                why_confusable=cand.get("why_confusable", "Shares the same name."),
                why_different=cand.get("why_different", "Could not be corroborated as this person."),
            )
        )
    return matches, new_sources


def extract_related_personalities(
    person_name: str, activity: list[dict], sources: list[Source]
) -> list[RelatedPersonality]:
    """Heuristic only: scans activity summaries and source excerpts for
    capitalized name-like phrases co-occurring with the subject's own
    content. No relationship graph is available, so every result is
    labeled "possible" — never "confirmed" — and must be read as a lead
    for human review, not a verified connection."""
    own_name = person_name.strip().lower()
    counts: dict[str, dict] = {}

    def scan(text: str | None, source_id: str | None):
        if not text:
            return
        for match in _NAME_PATTERN.finditer(text):
            candidate = match.group(1).strip()
            if candidate.lower() == own_name or candidate.split()[0] in _STOPWORD_STARTS:
                continue
            entry = counts.setdefault(
                candidate, {"count": 0, "evidence": text[:200], "source_ids": set()}
            )
            entry["count"] += 1
            if source_id:
                entry["source_ids"].add(source_id)

    for item in activity:
        scan(item.get("summary"), (item.get("source_ids") or [None])[0])
    for s in sources:
        scan(s.excerpt, s.id)

    ranked = sorted(counts.items(), key=lambda kv: kv[1]["count"], reverse=True)
    results: list[RelatedPersonality] = []
    for name, info in ranked[:MAX_RELATED_PERSONALITIES]:
        if not info["source_ids"]:
            continue
        results.append(
            RelatedPersonality(
                name=name,
                connection_type="mentioned alongside this person in public content",
                strength=ConnectionStrength.POSSIBLE,
                evidence=info["evidence"],
                source_ids=sorted(info["source_ids"]),
            )
        )
    return results


def enrich_brief(
    brief: ProspectBrief,
    *,
    person_data: dict | None,
    linkedin_url: str | None,
    education_records: list[dict],
    profile_source_id: str | None,
    company_research: dict | None,
    same_name_candidates: list[dict],
    activity: list[dict],
) -> ProspectBrief:
    identity_verification = build_identity_verification(person_data, linkedin_url)
    education = build_education_entries(education_records, profile_source_id, brief.sources)
    company_profiles = build_company_profiles(brief, company_research)
    detailed_summary = build_detailed_summary(brief)
    same_name_people, sources_with_namesakes = build_same_name_people(
        same_name_candidates, brief.sources
    )
    related_personalities = extract_related_personalities(
        brief.prospect_name, activity, sources_with_namesakes
    )

    enriched = brief.model_copy(
        update={
            "identity_verification": identity_verification,
            "education": education,
            "company_profiles": company_profiles,
            "detailed_summary": detailed_summary,
            "same_name_people": same_name_people,
            "related_personalities": related_personalities,
            "sources": sources_with_namesakes,
        }
    )
    return validate_brief(enriched)
