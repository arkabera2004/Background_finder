from app.schemas.profile import EducationRecord, Experience
from app.services.identity_attribution import (
    augment_fingerprint_with_mentions,
    build_fingerprint,
    canonical_url,
    normalized_title,
    score_item,
)


def _fp(**overrides):
    fp = build_fingerprint(
        full_name="Vineet Shukla",
        linkedin_url="https://linkedin.com/in/shuklavineet",
        current_company="JoulestoWatts Business Solutions",
        headline="AI & Data Science Visionary, Hands-On CTO",
        experiences=[
            Experience(title="VP, Head of Data", company="Mahindra Group"),
            Experience(title="Senior Director, Data Science and ML", company="UnitedHealth Group"),
        ],
        education=[EducationRecord(institution="IIM Bangalore"), EducationRecord(institution="MNNIT Allahabad")],
    )
    for key, value in overrides.items():
        setattr(fp, key, value)
    return fp


def test_subjects_own_coverage_scores_as_subject_via_past_employer():
    """Regression for F1: the subject's own interview about a past role
    (not the current employer) must not be rejected for lacking a match
    against the *current* employer alone."""
    fp = _fp()
    text = "Vineet Shukla, CTO, Mahindra Teqo, formerly Head of Data at Mahindra Group"
    verdict, score = score_item(text, fp)
    assert verdict == "subject"
    assert score >= 1


def test_item_with_no_fingerprint_hit_is_unverified_not_namesake():
    """Regression: absence of corroboration must not be treated as proof
    of a different person — that was the old (wrong) behavior."""
    fp = _fp()
    text = "Vineet Shukla speaking at an industry event, October 2026"
    verdict, _ = score_item(text, fp)
    assert verdict == "unverified"


def test_item_matching_a_known_other_employer_is_namesake():
    fp = _fp(known_other_employers={"HCLTech"})
    text = "Vineet Shukla, VP and Regional Business Head at HCLTech, speaks at GITEX 2025"
    verdict, _ = score_item(text, fp)
    assert verdict == "namesake"


def test_namesake_conflict_does_not_override_a_real_corroborated_match():
    """If the same text also corroborates the subject's own fingerprint, a
    coincidental generic-word overlap with a known-other-employer string
    must not force a false namesake verdict."""
    fp = _fp(known_other_employers={"HCLTech"})
    text = "Vineet Shukla, CTO at Mahindra Teqo, formerly of Mahindra Group"
    verdict, _ = score_item(text, fp)
    assert verdict == "subject"


def test_text_not_mentioning_the_name_is_dropped():
    fp = _fp()
    verdict, _ = score_item("JoulestoWatts announces a new product launch", fp)
    assert verdict == "drop"


def test_augment_fingerprint_recovers_fresh_item_a_thin_profile_would_reject():
    """Regression: namesake-11 in the audit — an MNNIT Allahabad alumni-event
    post naming the subject as "CTO, Founder" was rejected because the
    profile snapshot had no education data at all. Scanning the run's own
    results for institution mentions co-occurring with the subject's name
    must recover this before scoring."""
    fp = _fp(employers=set(), titles=set(), schools=set())  # simulate a thin snapshot
    texts = [
        "Vineet Shukla, CTO, Founder, at the MNNIT E-Summit Renaissance 2026, "
        "shares 20+ years in AI, GenAI, and data."
    ]
    augment_fingerprint_with_mentions(fp, texts)
    verdict, _ = score_item(texts[0], fp)
    assert verdict == "subject"


def test_augment_fingerprint_ignores_mentions_in_text_without_the_subjects_name():
    """An institution mentioned in a result about someone else must not
    leak into the fingerprint."""
    fp = _fp(employers=set(), titles=set(), schools=set())
    augment_fingerprint_with_mentions(fp, ["Someone Else graduated from MNNIT Allahabad."])
    assert fp.schools == set()


def test_generic_institution_words_dont_create_a_false_match():
    """Regression caught live: "Indian Institute of Technology" (a real
    certification, legitimately in the fingerprint) and "Institute for
    Plasma Research" (an unrelated namesake's affiliation) share only the
    structural word "institute" — that must not count as corroboration."""
    fp = _fp(schools={"Indian Institute of Technology"})
    text = (
        "Vineet Shukla, Post Doctoral Fellow, Institute for Plasma Research, "
        "Gandhinagar. Cited by 24. Contact Vineet Shukla."
    )
    verdict, _ = score_item(text, fp)
    assert verdict != "subject"


def test_canonical_url_merges_www_and_in_subdomain_and_query_string():
    a = canonical_url("https://www.linkedin.com/in/shuklavineet/")
    b = canonical_url("https://in.linkedin.com/in/shuklavineet?trk=public")
    assert a == b


def test_normalized_title_ignores_punctuation_and_case():
    assert normalized_title("Mahindra Teqo: CTO Appointment!") == normalized_title(
        "mahindra teqo cto appointment"
    )
