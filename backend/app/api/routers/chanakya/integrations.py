"""Integrations status — which providers Chanakya's agents run on and
their real configured state, never a secret value. Mirrors the
reference app's "Integrations and schedule" page: name, purpose, and
live connection state per provider, not a settings dump.
"""

from fastapi import APIRouter, Depends

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.config import settings

router = APIRouter(prefix="/chanakya")


def _provider_status(name: str, purpose: str, active: bool, configured: bool, note: str) -> dict:
    if active:
        status = "active"
    elif configured:
        status = "configured, not selected"
    else:
        status = "not configured"
    return {"name": name, "purpose": purpose, "status": status, "note": note}


@router.get("/integrations")
async def list_integrations(_user: AuthenticatedUser = Depends(get_current_user)) -> list[dict]:
    search = settings.search_provider
    ai = settings.ai_provider
    extraction = settings.extraction_provider
    email_verification = settings.email_verification_provider

    return [
        _provider_status(
            "DuckDuckGo",
            "Company and people discovery, LinkedIn identity search",
            active=search == "duckduckgo",
            configured=True,
            note="Free, keyless — no account required.",
        ),
        _provider_status(
            "Tavily",
            "Paid search alternative to DuckDuckGo",
            active=search == "tavily",
            configured=bool(settings.tavily_api_key),
            note="Real key present but not selected — switching back requires explicit approval (real quota).",
        ),
        _provider_status(
            "Local extraction (trafilatura)",
            "Company website crawling",
            active=extraction == "local",
            configured=True,
            note="Free, keyless.",
        ),
        _provider_status(
            "Firecrawl",
            "Paid crawling alternative",
            active=extraction == "firecrawl",
            configured=bool(settings.firecrawl_api_key),
            note="Real key present but not selected.",
        ),
        _provider_status(
            "Gemini",
            "Brief synthesis, email drafting",
            active=ai == "gemini",
            configured=bool(settings.gemini_api_key),
            note="Configured; not called without explicit go-ahead (real quota).",
        ),
        _provider_status(
            "Anthropic",
            "Alternate AI provider",
            active=ai == "anthropic",
            configured=bool(settings.anthropic_api_key),
            note="No key configured.",
        ),
        _provider_status(
            "NeverBounce",
            "Real email verification",
            active=email_verification == "neverbounce",
            configured=bool(settings.neverbounce_api_key),
            note="No key configured — falls back to a free MX-check heuristic.",
        ),
        _provider_status(
            "Supabase",
            "Authentication, tenant database",
            active=True,
            configured=bool(settings.supabase_url),
            note="Session auth verified via JWKS.",
        ),
    ]
