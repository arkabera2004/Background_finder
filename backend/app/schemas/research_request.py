from pydantic import BaseModel, model_validator

from app.schemas.research import normalize_linkedin_profile_url

VALID_DEPTHS = ("quick", "standard", "deep")


class ResearchRequest(BaseModel):
    """Exactly one intake method must be provided."""

    linkedin_url: str | None = None
    full_name: str | None = None
    company: str | None = None
    pasted_text: str | None = None
    depth: str = "standard"

    @model_validator(mode="after")
    def check_intake_method(self) -> "ResearchRequest":
        if self.depth not in VALID_DEPTHS:
            raise ValueError(f"depth must be one of {VALID_DEPTHS}")

        if self.linkedin_url:
            self.linkedin_url = normalize_linkedin_profile_url(self.linkedin_url)
            return self

        if self.pasted_text:
            if not self.full_name:
                raise ValueError("full_name is required when submitting pasted_text")
            if len(self.pasted_text.strip()) < 50:
                raise ValueError("pasted_text must be at least 50 characters")
            return self

        if self.full_name and self.company:
            return self

        raise ValueError(
            "Provide exactly one intake method: linkedin_url, (full_name + company), "
            "or (full_name + pasted_text)."
        )
