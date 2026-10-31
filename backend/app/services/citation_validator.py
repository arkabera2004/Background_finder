from app.schemas.brief import ActivityItem, CareerEntry, Claim, PersonalizationHook, ProspectBrief

MIN_HOOKS = 3


def _valid_source_ids(claim_source_ids: list[str], known_ids: set[str]) -> list[str]:
    return [sid for sid in claim_source_ids if sid in known_ids]


def _claim_is_supported(claim: Claim, known_ids: set[str]) -> bool:
    """A non-inference claim needs at least one valid source; inferences are
    explicitly allowed to be unsourced (they're flagged as inferences, not facts)."""
    if claim.is_inference:
        return True
    return len(_valid_source_ids(claim.source_ids, known_ids)) > 0


def validate_brief(brief: ProspectBrief) -> ProspectBrief:
    """Drop claims with no valid source (unless marked as an inference) and
    drop career entries/activity items/hooks with no valid source. Never
    mutates in place; returns a new, cleaned brief. Never invents a
    replacement source."""
    known_ids = {s.id for s in brief.sources}

    def clean_claims(claims: list[Claim]) -> list[Claim]:
        kept = []
        for c in claims:
            if _claim_is_supported(c, known_ids):
                kept.append(
                    c.model_copy(update={"source_ids": _valid_source_ids(c.source_ids, known_ids)})
                )
        return kept

    def clean_career_entries(entries: list[CareerEntry]) -> list[CareerEntry]:
        kept = []
        for e in entries:
            valid = _valid_source_ids(e.source_ids, known_ids)
            if valid:
                kept.append(e.model_copy(update={"source_ids": valid}))
        return kept

    def clean_activity_items(items: list[ActivityItem]) -> list[ActivityItem]:
        kept = []
        for i in items:
            valid = _valid_source_ids(i.source_ids, known_ids)
            if valid:
                kept.append(i.model_copy(update={"source_ids": valid}))
        return kept

    def clean_hooks(hooks: list[PersonalizationHook]) -> list[PersonalizationHook]:
        kept = []
        for h in hooks:
            valid = _valid_source_ids(h.source_ids, known_ids)
            if valid:
                kept.append(h.model_copy(update={"source_ids": valid}))
        return kept

    return brief.model_copy(
        update={
            "snapshot": clean_claims(brief.snapshot),
            "current_role": clean_claims(brief.current_role),
            "company_overview": clean_claims(brief.company_overview),
            "career_timeline": clean_career_entries(brief.career_timeline),
            "expertise": clean_claims(brief.expertise),
            "activity": clean_activity_items(brief.activity),
            "recurring_themes": clean_claims(brief.recurring_themes),
            "company_context": clean_claims(brief.company_context),
            "communication_style": clean_claims(brief.communication_style),
            "likely_priorities": clean_claims(brief.likely_priorities),
            "personalization_hooks": clean_hooks(brief.personalization_hooks),
        }
    )


def has_enough_hooks(brief: ProspectBrief) -> bool:
    return len(brief.personalization_hooks) >= MIN_HOOKS
