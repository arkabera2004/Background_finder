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
from app.schemas.brief import (
    ActivityItem,
    CareerEntry,
    Claim,
    Confidence,
    OutreachStrategy,
    ProspectBrief,
    ResearchGaps,
    Source,
)
from app.services.citation_validator import validate_brief

SYSTEM_INSTRUCTIONS = """You are producing a structured Prospect Brief as JSON.

Rules you MUST follow:
- Only use facts present in the provided research data below. Never invent names, titles, companies, dates, or events.
- Every factual claim in snapshot/current_role/company_overview/expertise/recurring_themes/company_context/communication_style/likely_priorities MUST either:
  (a) include a source_ids list referencing one of the provided source "id" values, OR
  (b) be marked "is_inference": true if it's a reasonable inference rather than a directly observed fact.
- Each claim object may also include an optional "date" field (string, e.g. "2026-03" or "2026-03-15"). Populate it when the claim describes a specific dated event or announcement (e.g. company news, a funding round, a product launch); otherwise leave it null. Never invent a date that isn't supported by the source.
- NEVER invent a source_id that isn't in the provided sources list. NEVER invent a URL.
- career_timeline entries must come only from the supplied career data, verbatim or lightly reworded — do not add entries, do not invent dates or roles.
- activity entries must come only from supplied activity data — do not add entries.
- Generate 0-7 "personalization_hooks", each with source_ids referencing only provided sources. If there isn't enough material, return fewer hooks or none — do not pad with generic flattery.
- If sources conflict (e.g. two different dates/companies for the same role), add an entry to research_gaps.conflicting_information describing the conflict instead of picking one silently.
- List anything notably missing (e.g. no company data found, no recent activity found) in research_gaps.missing_information.
- If a "KNOWN RESEARCH GAPS" list is provided below, copy each of those gap strings VERBATIM into research_gaps.missing_information (in addition to anything else you identify).
- Output ONLY valid JSON matching this exact shape, no prose, no markdown fences:
{
  "prospect_name": string,
  "snapshot": [{"text": string, "source_ids": [string], "confidence": "high"|"medium"|"low", "is_inference": bool, "date": string|null}],
  "current_role": [...same claim shape...],
  "company_overview": [...same claim shape...],
  "career_timeline": [{"organization": string, "title": string, "start_date": string|null, "end_date": string|null, "description": string|null, "source_ids": [string], "confidence": "high"|"medium"|"low"}],
  "expertise": [...same claim shape...],
  "activity": [{"activity_type": string, "topic": string, "summary": string, "url": string, "published_at": string|null, "authored_by_person": bool, "relevance": string|null, "confidence": "high"|"medium"|"low", "source_ids": [string]}],
  "recurring_themes": [...same claim shape...],
  "company_context": [...same claim shape...],
  "communication_style": [...same claim shape...],
  "likely_priorities": [...same claim shape...],
  "personalization_hooks": [{"evidence": string, "relevance": string, "outreach_angle": string, "source_ids": [string], "confidence": "high"|"medium"|"low"}],
  "outreach_strategy": {"angle": string|null, "primary_hooks": [string], "question_or_value_prop": string|null, "opening_approach": string|null, "avoid": [string]},
  "research_gaps": {"missing_information": [string], "limited_coverage_areas": [string], "conflicting_information": [string], "unverified_claims": [string], "inaccessible_sources": [string]}
}
"""


def _extract_json(text: str) -> dict:
    """Models sometimes wrap JSON in markdown fences despite instructions."""
    stripped = text.strip()
    fence_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", stripped, re.DOTALL)
    if fence_match:
        stripped = fence_match.group(1)
    return json.loads(stripped)


def build_prompt(
    person_data: dict,
    career: dict,
    activity: list[dict],
    sources: list[Source],
    company_gaps: list[str] | None = None,
) -> str:
    sources_block = "\n".join(
        f'- id="{s.id}" url="{s.url}" title="{s.title or ""}" excerpt="{(s.excerpt or "")[:200]}"'
        for s in sources
    ) or "(no sources available)"

    gaps_block = ""
    if company_gaps:
        gaps_list = "\n".join(f"- {g}" for g in company_gaps)
        gaps_block = f"\nKNOWN RESEARCH GAPS (copy verbatim into research_gaps.missing_information):\n{gaps_list}\n"

    return (
        f"{SYSTEM_INSTRUCTIONS}\n\n"
        f"RESEARCH DATA:\n"
        f"Person: {json.dumps(person_data, default=str)}\n"
        f"Career analysis (career_timeline entries come from here, already structured — do not add entries): "
        f"{json.dumps(career, default=str)}\n"
        f"Activity (activity entries come from here, already structured — do not add entries): "
        f"{json.dumps(activity, default=str)}\n"
        f"Available sources (use ONLY these ids for citations):\n{sources_block}\n"
        f"{gaps_block}"
    )


async def synthesize_with_ai(
    provider: AiProvider,
    person_data: dict,
    career: dict,
    activity: list[dict],
    sources: list[Source],
    company_gaps: list[str] | None = None,
) -> tuple[ProspectBrief, dict]:
    """Raises on failure — caller is responsible for falling back to
    rule-based synthesis. Returns (brief, metadata) where metadata has
    provider/model/usage for cost tracking."""
    prompt = build_prompt(person_data, career, activity, sources, company_gaps)

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


def rule_based_synthesis(
    person_data: dict | None,
    career: dict,
    activity: list[dict],
    sources: list[Source],
    company_gaps: list[str] | None = None,
) -> tuple[ProspectBrief, dict]:
    """The deterministic fallback used whenever no AI provider is configured
    or the AI path fails. career_timeline and activity are structured data
    collected by earlier stages (not synthesized prose), so they're passed
    through verbatim here rather than summarised. The one piece of real work
    this function does is making sure every source_id those entries carry
    actually resolves to an entry in the sources list it returns — citation_
    validator applies a strict all-or-nothing rule to CareerEntry/ActivityItem,
    so a dangling source_id (e.g. the "profile" source id that earlier stages
    reference but never add to the shared sources list) would otherwise wipe
    the entire section out silently.
    """
    all_sources = list(sources)
    known_ids = {s.id for s in all_sources}

    def ensure_source(source_id: str, url: str | None) -> None:
        if source_id not in known_ids:
            all_sources.append(Source(id=source_id, url=url or "manual-entry"))
            known_ids.add(source_id)

    snapshot: list[Claim] = []
    current_role: list[Claim] = []
    if person_data:
        text = person_data.get("full_name", "Unknown")
        if person_data.get("headline"):
            text += f" — {person_data['headline']}"
        snapshot.append(
            Claim(text=text, is_inference=True, source_ids=[], confidence=Confidence.HIGH)
        )
        if person_data.get("headline"):
            current_role.append(
                Claim(
                    text=person_data["headline"],
                    is_inference=True,
                    source_ids=[],
                    confidence=Confidence.MEDIUM,
                )
            )

    profile_url = (person_data or {}).get("linkedin_url")

    career_timeline: list[CareerEntry] = []
    for entry in career.get("career_timeline", []):
        source_ids = entry.get("source_ids", [])
        for sid in source_ids:
            ensure_source(sid, profile_url)
        career_timeline.append(CareerEntry.model_validate(entry))

    activity_items: list[ActivityItem] = []
    for item in activity:
        source_ids = list(item.get("source_ids", []))
        if not source_ids:
            # Activity items carry their own url even when no source_id was
            # wired up by the collecting stage — mint a source for it rather
            # than lose the entry to citation_validator's strict rule.
            fallback_id = f"activity-{len(all_sources)}"
            ensure_source(fallback_id, item.get("url"))
            source_ids = [fallback_id]
        else:
            for sid in source_ids:
                ensure_source(sid, item.get("url"))
        activity_items.append(ActivityItem.model_validate({**item, "source_ids": source_ids}))

    missing_information: list[str] = []
    if not career_timeline:
        missing_information.append("No career timeline could be derived without AI synthesis")
    if not activity_items:
        missing_information.append("No activity could be derived without AI synthesis")
    missing_information.append("No company overview could be derived without AI synthesis")
    missing_information.append("No recurring themes could be derived without AI synthesis")
    missing_information.append("No company context could be derived without AI synthesis")
    missing_information.append("No expertise summary could be derived without AI synthesis")
    missing_information.append("No communication style assessment could be derived without AI synthesis")
    missing_information.append("No likely priorities could be derived without AI synthesis")
    missing_information.append("No personalization hooks could be derived without AI synthesis")
    if company_gaps:
        for gap in company_gaps:
            if gap not in missing_information:
                missing_information.append(gap)

    brief = ProspectBrief(
        prospect_name=person_data.get("full_name", "Unknown") if person_data else "Unknown",
        snapshot=snapshot,
        current_role=current_role,
        career_timeline=career_timeline,
        activity=activity_items,
        sources=all_sources,
        outreach_strategy=OutreachStrategy(angle=None),
        research_gaps=ResearchGaps(missing_information=missing_information),
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
