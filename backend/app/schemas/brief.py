from enum import Enum

from pydantic import BaseModel


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Source(BaseModel):
    id: str
    url: str
    title: str | None = None
    excerpt: str | None = None


class Claim(BaseModel):
    text: str
    source_ids: list[str] = []
    confidence: Confidence = Confidence.MEDIUM
    is_inference: bool = False


class Hook(BaseModel):
    text: str
    source_ids: list[str]
    confidence: Confidence = Confidence.MEDIUM


class ProspectBrief(BaseModel):
    prospect_name: str
    snapshot: list[Claim] = []
    career_story: list[Claim] = []
    current_role: list[Claim] = []
    company: list[Claim] = []
    content_and_interests: list[Claim] = []
    communication_style: list[Claim] = []
    hooks: list[Hook] = []
    likely_priorities: list[Claim] = []
    dos_and_donts: list[str] = []
    sources: list[Source] = []
