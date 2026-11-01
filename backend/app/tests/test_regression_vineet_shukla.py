"""Offline deterministic regression fixture for the ProspectLens audit
"Vineet Shukla Research Run" (Nov 1 2026). Reproduces the exact failure
patterns documented there — a common name, a thin/stale profile snapshot
missing a recent job change, and a same-named senior tech executive — as a
fixture so the checks don't depend on live search results that may change.

The raw search-result JSON from the actual audited run was not available
to reconstruct this fixture; the canned results below are built to match
the documented evidence (titles/snippets/URLs referenced in the audit
report) as closely as possible, not a literal replay of a saved capture.
Page-11 checklist items this test exercises are marked inline.
"""

import pytest

from app.providers.company_crawler import NullCrawler
from app.providers.profile_provider import ProfileProvider
from app.providers.search_provider import SearchProvider, SearchResult
from app.schemas.profile import Experience, Person
from app.stages.base import StageContext, StageName
from app.stages.impl import (
    AnalyseActivityStage,
    AnalyseCareerStage,
    FetchProfileStage,
    ResearchCompanyStage,
    ResolveIdentityStage,
    SynthesiseBriefStage,
    WebFootprintStage,
)
from app.stages.pipeline import Pipeline

LINKEDIN_URL = "https://linkedin.com/in/shuklavineet"


class _ThinSnapshotProvider(ProfileProvider):
    """Reproduces the audited profile fetch: current employer and a partial
    experience history are present, but — as in the real stale/thin
    snapshot — no education data was captured by the provider. The
    deterministic regex fallback (F7) is what's expected to recover it
    from the press-coverage sources below, not this provider."""

    name = "fixture"

    async def fetch_profile(self, linkedin_url, pasted_text, full_name=None) -> Person:
        return Person(
            full_name="Vineet Shukla",
            headline="AI & Data Science Visionary, Hands-On CTO",
            current_company="JoulestoWatts Business Solutions",
            linkedin_url=linkedin_url,
            experiences=[
                Experience(title="CTO", company="JoulestoWatts Business Solutions", end_date=None),
                Experience(title="CTO", company="Mahindra Teqo"),
                Experience(title="VP, Head of Data", company="Mahindra Group"),
                Experience(
                    title="Senior Director, Data Science and ML", company="UnitedHealth Group"
                ),
            ],
            education=[],
            source=self.name,
        )


class _FixtureSearchProvider(SearchProvider):
    name = "fixture-search"

    def __init__(self, results_by_query_substring: dict[str, list[SearchResult]]):
        self._results = results_by_query_substring

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        for substring, results in self._results.items():
            if substring in query:
                return results[:max_results]
        return []


def _web_footprint_results() -> dict[str, list[SearchResult]]:
    return {
        "interview OR podcast": [
            # [namesake-0] in the audit: the subject's own interview about a
            # past role, wrongly rejected under the old "current employer
            # only" fingerprint. Correct answer: Subject.
            SearchResult(
                url="https://cloudai-summit.example/2024/vineet-shukla",
                title="Cloud+AI Innovation Summit 2024: Vineet Shukla, CTO, Mahindra Teqo",
                snippet=(
                    "Vineet Shukla, CTO at Mahindra Teqo, formerly Head of Data at "
                    "Mahindra Group, discusses running Mahindra's Data Center of "
                    "Excellence. He also holds an MBA in business analytics from "
                    "IIM Bangalore."
                ),
            ),
            # [activity-25]/[namesake-1] in the audit: a different person
            # entirely. Correct answer: Namesake (requires the conflict to be
            # known — seeded below via WebFootprintStage's constructor, same
            # mechanism the audit's own fix plan describes).
            SearchResult(
                url="https://entrepreneurme.example/gitex-2025-hcltech",
                title="Entrepreneur Middle East: Vineet Shukla, VP and Regional Business Head, HCLTech",
                snippet=(
                    "At GITEX 2025, HCLTech's Vineet Shukla, VP and Regional Business "
                    "Head based in the UAE, spoke about Global Capability Centers."
                ),
            ),
            # [activity-26]/[namesake-13] in the audit: no corroborating or
            # conflicting detail at all. Correct answer: Unverified, excluded.
            SearchResult(
                url="https://topmate.io/vineet_shukla91",
                title="Vineet Shukla — Interview prep & tips",
                snippet="Book a session with Vineet Shukla for interview prep and career tips.",
            ),
        ],
        "article OR publication": [
            # [namesake-10] in the audit: the subject's own appointment
            # announcement, also wrongly rejected previously. Correct
            # answer: Subject.
            SearchResult(
                url="https://cxojunction.example/vineet-shukla-mahindra-teqo-cto",
                title="CXO Junction: Vineet Shukla Appointed CTO of Mahindra Teqo",
                snippet=(
                    "Vineet Shukla has been appointed CTO of Mahindra Teqo. He is an "
                    "alumnus of MNNIT Allahabad."
                ),
            ),
        ],
        "talk OR conference OR webinar": [],
    }


@pytest.fixture(autouse=True)
def _safe_dns(monkeypatch):
    from app.services import company_discovery

    monkeypatch.setattr(company_discovery.socket, "gethostbyname", lambda host: "93.184.216.34")


@pytest.mark.asyncio
async def test_vineet_shukla_regression_fixture_matches_audit_acceptance_criteria():
    search = _FixtureSearchProvider(_web_footprint_results())

    stages = {
        StageName.RESOLVE_IDENTITY: ResolveIdentityStage(
            full_name="Vineet Shukla", linkedin_url=LINKEDIN_URL, company=None
        ),
        StageName.FETCH_PROFILE: FetchProfileStage(
            _ThinSnapshotProvider(), linkedin_url=LINKEDIN_URL, pasted_text=None
        ),
        StageName.ANALYSE_CAREER: AnalyseCareerStage(),
        StageName.RESEARCH_COMPANY: ResearchCompanyStage(NullCrawler(), search=search),
        StageName.ANALYSE_ACTIVITY: AnalyseActivityStage(),
        # known_other_employers is seeded from the HCLTech namesake already
        # confirmed in the audit's own ground-truth notes — exactly the
        # mechanism the audit's fix plan describes ("filled from namesakes
        # already confirmed in the run").
        StageName.WEB_FOOTPRINT: WebFootprintStage(search, known_other_employers={"HCLTech"}),
        StageName.SYNTHESISE_BRIEF: SynthesiseBriefStage(),
    }
    pipeline = Pipeline(stages)
    ctx = StageContext(run_id="regression-vineet-shukla", depth="standard")

    results = await pipeline.run(ctx)
    brief = results[StageName.SYNTHESISE_BRIEF].output

    sources_by_id = {s["id"]: s["url"] for s in brief["sources"]}
    activity_urls = {a["url"] for a in brief["activity"]}
    same_name_urls = {
        sources_by_id[sid] for m in brief["same_name_people"] for sid in m["source_ids"]
    }

    # [ ] namesake-0 and namesake-10 classified as Subject
    assert "https://cloudai-summit.example/2024/vineet-shukla" in activity_urls
    assert "https://cxojunction.example/vineet-shukla-mahindra-teqo-cto" in activity_urls

    # [ ] activity-25/[s20] and [namesake-1] classified as Namesake (HCLTech)
    assert "https://entrepreneurme.example/gitex-2025-hcltech" in same_name_urls
    assert "https://entrepreneurme.example/gitex-2025-hcltech" not in activity_urls

    # [ ] activity-26/[s21] and [namesake-13] classified as Unverified and excluded
    assert "https://topmate.io/vineet_shukla91" not in activity_urls
    assert "https://topmate.io/vineet_shukla91" not in same_name_urls

    # [ ] No item appears in more than one bucket
    assert activity_urls.isdisjoint(same_name_urls)

    # [ ] Education lists IIM Bangalore and MNNIT Allahabad, even with no AI key
    institutions = {e["institution"] for e in brief["education"]}
    assert "IIM Bangalore" in institutions
    assert "MNNIT Allahabad" in institutions

    # [ ] Career timeline lists UnitedHealth Group, Mahindra Group, Mahindra
    #     Teqo, JoulestoWatts
    orgs = {c["organization"] for c in brief["career_timeline"]}
    assert orgs == {
        "UnitedHealth Group",
        "Mahindra Group",
        "Mahindra Teqo",
        "JoulestoWatts Business Solutions",
    }

    # [ ] Stale-role warning shown (no dated evidence at all in this fixture,
    #     matching the audit: current role is "User (not yet in public sources)")
    assert any(
        "could not be confirmed" in g or "out of date" in g
        for g in brief["research_gaps"]["limited_coverage_areas"]
    )

    # [ ] Related Personalities contains only people (no publisher/industry
    #     terms like "Entrepreneur Middle East" or "Global Capability Centers")
    related_names = {p["name"] for p in brief["related_personalities"]}
    assert "Entrepreneur Middle East" not in related_names
    assert "Global Capability Centers" not in related_names

    # identity_verification anchored on the LinkedIn URL
    assert brief["identity_verification"]["profile_url"] == LINKEDIN_URL
    assert brief["identity_verification"]["confidence"] == "high"
