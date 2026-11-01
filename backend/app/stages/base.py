from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class StageName(str, Enum):
    RESOLVE_IDENTITY = "resolve_identity"
    FETCH_PROFILE = "fetch_profile"
    ANALYSE_CAREER = "analyse_career"
    RESEARCH_COMPANY = "research_company"
    ANALYSE_ACTIVITY = "analyse_activity"
    WEB_FOOTPRINT = "web_footprint"
    SYNTHESISE_BRIEF = "synthesise_brief"


@dataclass
class StageContext:
    """Shared, mutable state passed between stages in a single run."""

    run_id: str
    depth: str
    outputs: dict[str, Any] = field(default_factory=dict)
    # Populated with the exception from a non-critical parallel stage that
    # failed, keyed by StageName, so synthesis can report it as a research
    # gap instead of the failure silently vanishing.
    stage_failures: dict["StageName", BaseException] = field(default_factory=dict)


@dataclass
class StageResult:
    stage: StageName
    output: dict[str, Any]
    sources: list[dict[str, Any]] = field(default_factory=list)


class Stage(ABC):
    name: StageName

    @abstractmethod
    async def run(self, ctx: StageContext) -> StageResult: ...
