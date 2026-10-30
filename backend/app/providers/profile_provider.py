from abc import ABC, abstractmethod

from app.schemas.profile import Person


class ProviderUnavailableError(Exception):
    """Raised when a provider cannot fetch a profile (no credentials, rate limited, etc)."""


class ProfileProvider(ABC):
    name: str

    @abstractmethod
    async def fetch_profile(
        self, linkedin_url: str | None, pasted_text: str | None, full_name: str | None = None
    ) -> Person: ...


class ManualProvider(ProfileProvider):
    """Builds a Person from user-pasted text or a manually supplied name.

    Always available — requires no credentials or network access. Used as the
    guaranteed fallback when no paid provider is configured, and as the only
    path for the "paste profile text" and "PDF upload" intake methods.
    """

    name = "manual"

    async def fetch_profile(
        self, linkedin_url: str | None, pasted_text: str | None, full_name: str | None = None
    ) -> Person:
        if not pasted_text:
            raise ProviderUnavailableError(
                "ManualProvider requires pasted_text; no scraping is performed."
            )
        # The user-supplied name is authoritative; only guess from the text
        # itself when no name was explicitly given (e.g. a bare PDF export
        # with no separate name field).
        resolved_name = full_name.strip() if full_name else _guess_name_from_text(pasted_text)
        return Person(
            full_name=resolved_name,
            headline=_guess_headline_from_text(pasted_text),
            linkedin_url=linkedin_url,
            source=self.name,
        )


def _guess_name_from_text(text: str) -> str:
    first_line = text.strip().splitlines()[0].strip()
    return first_line[:120] if first_line else "Unknown"


def _guess_headline_from_text(text: str) -> str | None:
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    return lines[1][:200] if len(lines) > 1 else None
