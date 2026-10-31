"""AI-based Prospect Brief synthesis.

Builds a structured prompt from real stage outputs, asks the configured
AiProvider for JSON matching ProspectBrief's shape, validates it, and
runs it through the same citation_validator used by rule-based synthesis
— so even if the model hallucinates a source_id or URL, it gets dropped,
never surfaced. Falls back to rule-based synthesis (app/stages/impl.py's
original logic, reused here) on any AI failure, and the output always
says which path was actually used via `synthesis_method`.
"""

import json
import re

from pydantic import ValidationError

from app.providers.ai_provider import AiProvider, AiProviderError
from app.schemas.brief import Claim, Confidence, Hook, ProspectBrief, Source
from app.services.citation_validator import validate_brief

SYSTEM_INSTRUCTIONS = """You are producing a structured Prospect Brief as JSON.

Rules you MUST follow:
- Only use facts present in the provided research data below. Never invent names, titles, companies, dates, or events.
- Every factual claim in snapshot/career_story/current_role/company/content_and_interests/communication_style/likely_priorities MUST either:
  (a) include a source_ids list referencing one of the provided source "id" values, OR
  (b) be marked "is_inference": true if it's a reasonable inference rather than a directly observed fact.
- NEVER invent a source_id that isn't in the provided sources list. NEVER invent a URL.
- Generate 0-7 "hooks" (personalisation hooks), each with source_ids referencing only provided sources. If there isn't enough material, return fewer hooks or none — do not pad with generic flattery.
- Output ONLY valid JSON matching this exact shape, no prose, no markdown fences:
{
  "prospect_name": string,
  "snapshot": [{"text": string, "source_ids": [string], "confidence": "high"|"medium"|"low", "is_inference": bool}],
  "career_story": [...same claim shape...],
  "current_role": [...same claim shape...],
  "company": [...same claim shape...],
  "content_and_interests": [...same claim shape...],
  "communication_style": [...same claim shape...],
  "likely_priorities": [...same claim shape...],
  "hooks": [{"text": string, "source_ids": [string], "confidence": "high"|"medium"|"low"}],
  "dos_and_donts": [string]
}
"""


def _extract_json(text: str) -> dict:
    """Models sometimes wrap JSON in markdown fences despite instructions."""
    stripped = text.strip()
    fence_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", stripped, re.DOTALL)
    if fence_match:
        stripped = fence_match.group(1)
    return json.loads(stripped)


def build_prompt(person_data: dict, career: dict, sources: list[Source]) -> str:
    sources_block = "\n".join(
        f'- id="{s.id}" url="{s.url}" title="{s.title or ""}" excerpt="{(s.excerpt or "")[:200]}"'
        for s in sources
    ) or "(no sources available)"

    return (
        f"{SYSTEM_INSTRUCTIONS}\n\n"
        f"RESEARCH DATA:\n"
        f"Person: {json.dumps(person_data, default=str)}\n"
        f"Career analysis: {json.dumps(career, default=str)}\n"
        f"Available sources (use ONLY these ids for citations):\n{sources_block}\n"
    )


async def synthesize_with_ai(
    provider: AiProvider, person_data: dict, career: dict, sources: list[Source]
) -> tuple[ProspectBrief, dict]:
    """Raises on failure — caller is responsible for falling back to
    rule-based synthesis. Returns (brief, metadata) where metadata has
    provider/model/usage for cost tracking."""
    prompt = build_prompt(person_data, career, sources)

    last_error: Exception | None = None
    for attempt in range(2):  # one retry on invalid structured output
        # "Thinking" models (e.g. gemini-3.8-flash) spend part of max_tokens
        # on internal reasoning before the visible JSON — confirmed live,
        # 2048 tokens was ~1800 thinking + a truncated, invalid-JSON
        # remainder, every single call. 8192 leaves real room for both the
        # model's reasoning and a full multi-section brief. Timeout matches:
        # a structured-JSON synthesis prompt on a thinking model routinely
        # takes over a minute; the provider's 30s default was timing out
        # every real call here, not just slow ones.
        completion = await provider.complete(prompt, max_tokens=8192, timeout_seconds=120.0)
        try:
            raw = _extract_json(completion.text)
            raw["sources"] = [s.model_dump() for s in sources]  # never trust model-echoed sources
            brief = ProspectBrief.model_validate(raw)
        except (json.JSONDecodeError, ValidationError) as exc:
            last_error = exc
            prompt = (
                prompt
                + f"\n\nYour previous response was invalid ({exc}). "
                "Return ONLY the corrected JSON object, nothing else."
            )
            continue

        validated = validate_brief(brief)
        metadata = {
            "synthesis_method": "ai",
            "provider": completion.provider,
            "model": completion.model,
            "input_tokens": completion.usage.input_tokens,
            "output_tokens": completion.usage.output_tokens,
            "estimated_cost_usd": completion.usage.estimated_cost_usd,
        }
        return validated, metadata

    raise AiProviderError(f"AI synthesis produced invalid output twice: {last_error}")


def rule_based_synthesis(person_data: dict | None, career: dict, sources: list[Source]) -> tuple[ProspectBrief, dict]:
    """The original deterministic fallback — identical behavior to before
    AI synthesis existed, used whenever no AI provider is configured or
    the AI path fails."""
    snapshot = []
    if person_data:
        text = person_data.get("full_name", "Unknown")
        if person_data.get("headline"):
            text += f" — {person_data['headline']}"
        snapshot.append(
            Claim(text=text, is_inference=True, source_ids=[], confidence=Confidence.HIGH)
        )

    career_claims = []
    if career.get("total_months_experience"):
        career_claims.append(
            Claim(
                text=f"Approximately {career['total_months_experience']} months of tracked experience.",
                is_inference=True,
                confidence=Confidence.MEDIUM,
            )
        )

    hooks = [Hook(text=f"Mentioned in: {s.title or s.url}", source_ids=[s.id]) for s in sources[:7]]

    brief = ProspectBrief(
        prospect_name=person_data.get("full_name", "Unknown") if person_data else "Unknown",
        snapshot=snapshot,
        career_story=career_claims,
        sources=sources,
        hooks=hooks,
    )
    metadata = {
        "synthesis_method": "rule_based",
        "provider": None,
        "model": None,
        "input_tokens": 0,
        "output_tokens": 0,
        "estimated_cost_usd": 0.0,
    }
    return validate_brief(brief), metadata
