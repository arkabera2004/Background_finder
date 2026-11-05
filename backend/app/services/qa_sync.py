"""Agent 07 — QA and Sync: confidence scoring, email drafting, export rows.

Scoring and drafting here only ever read what earlier agents already
produced (identity confirmation, email verification, research brief
status/content) — it never invents a fact to raise a score or fill a
draft. A low score routes to human review instead of being hidden.
"""

CONFIDENCE_THRESHOLDS = {"high": 2.5, "medium": 1.5}


def score_confidence(identity_confirmed: bool, email_statuses: list[str], brief_status: str | None) -> dict:
    score = 0.0
    if identity_confirmed:
        score += 1.0
    if "valid" in email_statuses:
        score += 1.0
    elif "needs_review" in email_statuses:
        score += 0.5
    if brief_status == "completed":
        score += 1.0

    if score >= CONFIDENCE_THRESHOLDS["high"]:
        level = "high"
    elif score >= CONFIDENCE_THRESHOLDS["medium"]:
        level = "medium"
    else:
        level = "low"

    return {"score": score, "level": level, "needs_review": level == "low"}


def draft_email(full_name: str, offering_name: str, brief_data: dict) -> dict:
    """Builds a draft strictly from the brief's own content — a missing
    hook means a generic (not fabricated) opening, never an invented one."""
    first_name = full_name.split()[0] if full_name else "there"
    hooks = brief_data.get("personalization_hooks") or []
    strategy = brief_data.get("outreach_strategy") or {}

    opening = strategy.get("opening_approach")
    if not opening and hooks:
        opening = f"I noticed {hooks[0].get('evidence', 'your recent work')}."
    if not opening:
        opening = "I wanted to reach out given your role."

    value_prop = strategy.get("question_or_value_prop") or f"we help teams with {offering_name}"

    subject = f"{offering_name} — quick thought for {first_name}"
    body = (
        f"Hi {first_name},\n\n{opening}\n\n"
        f"Reaching out because {value_prop}. Open to a quick conversation?\n\nBest,"
    )
    return {"subject": subject, "body": body}
