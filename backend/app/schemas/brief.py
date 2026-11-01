from enum import Enum

from pydantic import BaseModel


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SourceType(str, Enum):
    COMPANY_WEBSITE = "company_website"
    COMPANY_NEWS = "company_news"
    NEWS_ARTICLE = "news_article"
    SOCIAL_PROFILE = "social_profile"
    SOCIAL_POST = "social_post"
    OTHER = "other"


class Source(BaseModel):
    id: str
    url: str
    title: str | None = None
    excerpt: str | None = None
    publisher: str | None = None
    source_type: SourceType = SourceType.OTHER
    published_at: str | None = None
    retrieved_at: str | None = None
    confidence: Confidence = Confidence.MEDIUM


class Claim(BaseModel):
    text: str
    source_ids: list[str] = []
    confidence: Confidence = Confidence.MEDIUM
    is_inference: bool = False
    date: str | None = None


class DatePrecision(str, Enum):
    EXACT = "exact"
    APPROXIMATE = "approximate"
    UNKNOWN = "unknown"


class CareerEntry(BaseModel):
    organization: str
    title: str
    start_date: str | None = None
    end_date: str | None = None
    date_precision: DatePrecision = DatePrecision.UNKNOWN
    description: str | None = None
    source_ids: list[str] = []
    confidence: Confidence = Confidence.MEDIUM


class IdentityVerification(BaseModel):
    """What anchored identity resolution and how confident we are that every
    other section describes this one person, not a namesake."""

    profile_url: str | None = None
    matched_identifiers: list[str] = []
    confidence: Confidence = Confidence.MEDIUM
    limitations: str | None = None


class EducationEntry(BaseModel):
    institution: str
    degree: str | None = None
    field: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    date_precision: DatePrecision = DatePrecision.UNKNOWN
    source_ids: list[str] = []
    confidence: Confidence = Confidence.MEDIUM


class CompanyProfile(BaseModel):
    """Per-organization detail for the Company-by-Company Overview section —
    one entry per company in the career timeline, not a generic description."""

    name: str
    website: str | None = None
    what_they_do: str | None = None
    industry: str | None = None
    person_role: str | None = None
    role_scope: str | None = None
    related_projects: list[str] = []
    start_date: str | None = None
    end_date: str | None = None
    date_precision: DatePrecision = DatePrecision.UNKNOWN
    source_ids: list[str] = []
    confidence: Confidence = Confidence.MEDIUM
    uncertainty_note: str | None = None


class SameNameMatch(BaseModel):
    """A different, publicly discoverable person sharing the name — kept
    strictly separate from the target's own facts to prevent misattribution."""

    name: str
    identity_summary: str
    distinguishing_info: str | None = None
    source_ids: list[str] = []
    why_confusable: str
    why_different: str


class ConnectionStrength(str, Enum):
    CONFIRMED = "confirmed"
    POSSIBLE = "possible"


class RelatedPersonality(BaseModel):
    name: str
    role: str | None = None
    connection_type: str
    strength: ConnectionStrength = ConnectionStrength.POSSIBLE
    evidence: str
    source_ids: list[str] = []


class ActivityType(str, Enum):
    ORIGINAL_POST = "original_post"
    REPOST_OR_SHARE = "repost_or_share"
    COMMENT = "comment"
    ARTICLE_OR_PUBLICATION = "article_or_publication"
    INTERVIEW_OR_PODCAST = "interview_or_podcast"
    TALK_OR_PRESENTATION = "talk_or_presentation"
    PROFESSIONAL_ANNOUNCEMENT = "professional_announcement"
    OTHER_PUBLIC_ACTIVITY = "other_public_activity"


class ActivityItem(BaseModel):
    activity_type: ActivityType
    topic: str
    summary: str
    url: str
    published_at: str | None = None
    authored_by_person: bool = True
    relevance: str | None = None
    confidence: Confidence = Confidence.MEDIUM
    source_ids: list[str] = []


class PersonalizationHook(BaseModel):
    evidence: str
    relevance: str
    outreach_angle: str
    source_ids: list[str]
    confidence: Confidence = Confidence.MEDIUM


class OutreachStrategy(BaseModel):
    angle: str | None = None
    primary_hooks: list[str] = []
    question_or_value_prop: str | None = None
    opening_approach: str | None = None
    avoid: list[str] = []


class ResearchGaps(BaseModel):
    missing_information: list[str] = []
    limited_coverage_areas: list[str] = []
    conflicting_information: list[str] = []
    unverified_claims: list[str] = []
    inaccessible_sources: list[str] = []


class ProspectBrief(BaseModel):
    prospect_name: str
    identity_verification: IdentityVerification | None = None
    snapshot: list[Claim] = []
    detailed_summary: list[Claim] = []
    education: list[EducationEntry] = []
    current_role: list[Claim] = []
    company_overview: list[Claim] = []
    company_profiles: list[CompanyProfile] = []
    career_timeline: list[CareerEntry] = []
    achievements: list[Claim] = []
    expertise: list[Claim] = []
    activity: list[ActivityItem] = []
    recurring_themes: list[Claim] = []
    company_context: list[Claim] = []
    communication_style: list[Claim] = []
    likely_priorities: list[Claim] = []
    same_name_people: list[SameNameMatch] = []
    related_personalities: list[RelatedPersonality] = []
    personalization_hooks: list[PersonalizationHook] = []
    outreach_strategy: OutreachStrategy
    sources: list[Source] = []
    research_gaps: ResearchGaps = ResearchGaps()
