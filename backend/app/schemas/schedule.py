"""Phase 5 — durable monthly scheduler: CRUD payload shapes."""

from pydantic import BaseModel, Field, model_validator

from app.schemas.catalogue import OfferingInput


class ScheduleCreate(BaseModel):
    offerings: list[OfferingInput]
    filters: dict = Field(default_factory=dict)
    config: dict = Field(default_factory=dict)
    day_of_month: int = 1
    enabled: bool = True

    @model_validator(mode="after")
    def check_offerings_and_day(self) -> "ScheduleCreate":
        if not self.offerings:
            raise ValueError("at least one offering is required")
        if not 1 <= self.day_of_month <= 28:
            raise ValueError("day_of_month must be between 1 and 28")
        return self


class ScheduleUpdate(BaseModel):
    enabled: bool | None = None
