from app.schemas.brief import Claim, CareerEntry, Confidence, OutreachStrategy, ProspectBrief, Source
from app.services.brief_enrichment import (
    build_company_profiles,
    build_detailed_summary,
    build_education_entries,
    build_identity_verification,
    build_recency_warning,
    build_same_name_people,
    enrich_brief,
    extract_education_from_sources,
    extract_related_personalities,
)


def _brief(**kwargs) -> ProspectBrief:
    kwargs.setdefault("outreach_strategy", OutreachStrategy(angle=None))
    return ProspectBrief(prospect_name="Jane Doe", **kwargs)


def test_identity_verification_high_confidence_with_linkedin_url():
    v = build_identity_verification(
        {"full_name": "Jane Doe", "current_company": "Acme"}, "https://linkedin.com/in/jane-doe"
    )
    assert v.confidence == Confidence.HIGH
    assert v.profile_url == "https://linkedin.com/in/jane-doe"
    assert "Name: Jane Doe" in v.matched_identifiers


def test_identity_verification_medium_confidence_without_linkedin_url():
    v = build_identity_verification({"full_name": "Jane Doe"}, None)
    assert v.confidence == Confidence.MEDIUM
    assert v.profile_url is None


def test_build_education_entries_skips_entries_without_institution():
    entries = build_education_entries(
        [
            {"institution": "State University", "degree": "B.S.", "start_date": "2012"},
            {"degree": "No institution here"},
        ],
        profile_source_id="profile",
    )
    assert len(entries) == 1
    assert entries[0].institution == "State University"
    assert entries[0].source_ids == ["profile"]


def test_extract_education_from_sources_finds_iim_and_mnnit():
    """Regression (F7): with no AI synthesis and no structured provider
    education data, the press coverage already in hand (CXO Digital Pulse /
    AIM-style excerpts) must still surface known institutions."""
    sources = [
        Source(
            id="s1",
            url="https://cxodigitalpulse.example/article",
            title="Vineet Shukla appointed CTO of Mahindra Teqo",
            excerpt="Shukla holds an MBA in business analytics from IIM Bangalore.",
        ),
        Source(
            id="s2",
            url="https://aim.example/profile",
            title="Profile: Vineet Shukla",
            excerpt="He is an alumnus of MNNIT Allahabad.",
        ),
    ]
    records = extract_education_from_sources(sources)
    institutions = {r["institution"] for r in records}
    assert "IIM Bangalore" in institutions
    assert "MNNIT Allahabad" in institutions
    iim = next(r for r in records if r["institution"] == "IIM Bangalore")
    assert iim["degree"] == "MBA"
    assert iim["source_id"] == "s1"


def test_build_education_entries_falls_back_to_regex_when_no_provider_data():
    entries = build_education_entries(
        [],
        profile_source_id="profile",
        fallback_sources=[
            Source(
                id="s1",
                url="https://cxodigitalpulse.example/article",
                title="Profile",
                excerpt="MBA from IIM Bangalore.",
            )
        ],
    )
    assert len(entries) == 1
    assert entries[0].institution == "IIM Bangalore"
    assert entries[0].source_ids == ["s1"]


def test_build_education_entries_prefers_structured_data_over_fallback():
    entries = build_education_entries(
        [{"institution": "State University"}],
        profile_source_id="profile",
        fallback_sources=[
            Source(id="s1", url="https://example.com", title="IIM Bangalore MBA grad", excerpt="")
        ],
    )
    assert len(entries) == 1
    assert entries[0].institution == "State University"


def test_build_company_profiles_marks_researched_company():
    brief = _brief(
        career_timeline=[
            CareerEntry(organization="Acme Robotics", title="PM", source_ids=["s1"]),
            CareerEntry(organization="Globex Corp", title="PM", source_ids=["s2"]),
        ]
    )
    profiles = build_company_profiles(
        brief, {"company": "Acme Robotics", "domain_guess": "acme.example"}
    )
    assert len(profiles) == 2
    acme = next(p for p in profiles if p.name == "Acme Robotics")
    globex = next(p for p in profiles if p.name == "Globex Corp")
    assert acme.website == "https://acme.example"
    assert acme.uncertainty_note is None
    assert globex.website is None
    assert globex.uncertainty_note is not None


def test_build_detailed_summary_builds_chronological_narrative():
    brief = _brief(
        career_timeline=[
            CareerEntry(
                organization="Acme",
                title="PM",
                start_date="2021-06",
                end_date=None,
                source_ids=["s1"],
            ),
            CareerEntry(
                organization="Globex",
                title="APM",
                start_date="2018-01",
                end_date="2021-05",
                source_ids=["s2"],
            ),
        ]
    )
    summary = build_detailed_summary(brief)
    assert len(summary) == 2
    assert "2018-01" in summary[0].text
    assert "2021-06" in summary[1].text


def test_build_same_name_people_mints_sources():
    matches, sources = build_same_name_people(
        [
            {
                "name": "Jane Doe",
                "identity_summary": "CEO of a different company",
                "url": "https://example.com/namesake",
                "why_confusable": "Same name",
                "why_different": "Different employer",
            }
        ],
        [],
    )
    assert len(matches) == 1
    assert matches[0].source_ids == ["namesake-0"]
    assert sources[0].url == "https://example.com/namesake"


def test_extract_related_personalities_is_always_possible_strength():
    activity = [
        {
            "summary": "Jane Doe interviewed John Smith about robotics strategy.",
            "source_ids": ["s1"],
        }
    ]
    results = extract_related_personalities(_brief(), activity, [])
    assert all(r.strength == "possible" for r in results)
    names = [r.name for r in results]
    assert "John Smith" in names
    assert "Jane Doe" not in names


def test_extract_related_personalities_filters_non_person_phrases():
    """Regression (F9): a publisher name or industry term that matches the
    "Capitalized Word(s)" pattern must not be treated as a related person."""
    activity = [
        {
            "summary": "Jane Doe spoke to Entrepreneur Middle East about Global Capability Centers.",
            "source_ids": ["s1"],
        }
    ]
    results = extract_related_personalities(_brief(), activity, [])
    names = [r.name for r in results]
    assert "Entrepreneur Middle East" not in names
    assert "Global Capability Centers" not in names


def test_extract_related_personalities_ignores_non_subject_sources():
    """Regression (F9): a name mentioned only in a company-context source
    not backing any subject-attributed claim must not seed a guess."""
    brief = _brief(
        career_timeline=[CareerEntry(organization="Acme", title="PM", source_ids=["s1"])],
    )
    unrelated_source = Source(
        id="s2",
        url="https://example.com/unrelated",
        excerpt="Priya Mohan was hired as COO at a different company entirely.",
    )
    results = extract_related_personalities(brief, [], [unrelated_source])
    assert results == []


def test_recency_warning_fires_when_newest_source_is_stale():
    brief = _brief(
        current_role=[Claim(text="CTO at JoulestoWatts", source_ids=["s1"])],
        sources=[Source(id="s1", url="https://example.com", published_at="2024-01-15")],
    )
    warning = build_recency_warning(brief)
    assert warning is not None
    assert "2024-01-15" in warning


def test_recency_warning_absent_when_recent_source_exists():
    from datetime import datetime, timedelta, timezone

    recent = (datetime.now(timezone.utc) - timedelta(days=5)).date().isoformat()
    brief = _brief(
        current_role=[Claim(text="CEO at Wayam AI", source_ids=["s1"])],
        sources=[Source(id="s1", url="https://example.com", published_at=recent)],
    )
    assert build_recency_warning(brief) is None


def test_recency_warning_fires_with_no_dated_evidence_at_all():
    brief = _brief(current_role=[Claim(text="CTO at JoulestoWatts", source_ids=["s1"])])
    warning = build_recency_warning(brief)
    assert warning is not None
    assert "could not be confirmed" in warning


def test_recency_warning_absent_with_no_current_role_claims():
    brief = _brief()
    assert build_recency_warning(brief) is None


def test_enrich_brief_populates_all_new_sections():
    brief = _brief(
        sources=[Source(id="profile", url="https://linkedin.com/in/jane-doe")],
        career_timeline=[
            CareerEntry(organization="Acme", title="PM", source_ids=["profile"]),
        ],
    )
    enriched = enrich_brief(
        brief,
        person_data={"full_name": "Jane Doe", "linkedin_url": "https://linkedin.com/in/jane-doe"},
        linkedin_url="https://linkedin.com/in/jane-doe",
        education_records=[{"institution": "State University"}],
        profile_source_id="profile",
        company_research={"company": "Acme", "domain_guess": "acme.example"},
        same_name_candidates=[],
        activity=[],
    )
    assert enriched.identity_verification is not None
    assert enriched.identity_verification.confidence == Confidence.HIGH
    assert len(enriched.education) == 1
    assert len(enriched.company_profiles) == 1
    assert len(enriched.detailed_summary) >= 1
