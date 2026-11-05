"""Agent 04 — LinkedIn Resolver: manual review queue intake shape."""

from pydantic import BaseModel, model_validator


class ManualIdentityConfirmation(BaseModel):
    """A human picks the correct profile for a person the resolver
    couldn't confirm automatically (zero or multiple candidates)."""

    linkedin_url: str

    @model_validator(mode="after")
    def check_url(self) -> "ManualIdentityConfirmation":
        if "linkedin.com/in/" not in self.linkedin_url:
            raise ValueError("linkedin_url must be a linkedin.com/in/ profile URL")
        return self
