"""Agent 01 — Catalogue Agent: offering intake and ICP brief shape."""

from pydantic import BaseModel, Field, model_validator


class OfferingInput(BaseModel):
    """One accelerator/AI/software offering or consulting capability."""

    name: str
    description: str = ""
    icp_criteria: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_name(self) -> "OfferingInput":
        if not self.name.strip():
            raise ValueError("offering name must not be empty")
        return self


class MonthlyRunCreate(BaseModel):
    period: str  # "YYYY-MM"
    config: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def check_period(self) -> "MonthlyRunCreate":
        import re

        if not re.fullmatch(r"\d{4}-\d{2}", self.period):
            raise ValueError("period must be in YYYY-MM format")
        return self


class OfferingBriefInput(BaseModel):
    """Manual review/edit payload for Agent 01's monthly offering + ICP brief."""

    offerings: list[OfferingInput]
    filters: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def check_offerings(self) -> "OfferingBriefInput":
        if not self.offerings:
            raise ValueError("at least one offering is required")
        return self
