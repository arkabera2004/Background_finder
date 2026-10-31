import io
import json

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

# Claim-list sections: rendered as a bulleted list of Claim objects
# ({"text", "is_inference", "confidence", "source_ids", "date"}).
CLAIM_SECTION_TITLES = {
    "snapshot": "Snapshot",
    "current_role": "Current Role",
    "company_overview": "Company Overview",
    "expertise": "Expertise",
    "recurring_themes": "Recurring Themes",
    "company_context": "Company Context",
    "communication_style": "Communication Style",
    "likely_priorities": "Likely Priorities",
}

SECTION_TITLES = CLAIM_SECTION_TITLES  # backwards-compatible alias


def to_json(brief: dict) -> str:
    return json.dumps(brief, indent=2, default=str)


def _claim_line(claim: dict) -> str:
    marker = " _(inference)_" if claim.get("is_inference") else ""
    date = f" ({claim['date']})" if claim.get("date") else ""
    return f"- {claim['text']}{marker}{date} [{claim.get('confidence', 'medium')}]"


def _career_entry_line(entry: dict) -> str:
    dates = f"{entry.get('start_date') or '?'} – {entry.get('end_date') or 'present'}"
    line = f"- **{entry.get('title', '')}** at **{entry.get('organization', '')}** ({dates})"
    if entry.get("description"):
        line += f" — {entry['description']}"
    return line


def _activity_line(item: dict) -> str:
    activity_type = (item.get("activity_type") or "").replace("_", " ")
    published = f" ({item['published_at']})" if item.get("published_at") else ""
    url = item.get("url") or ""
    url_part = f" — [{url}]({url})" if url else ""
    return f"- [{activity_type}] {item.get('topic', '')}{published}{url_part}"


def _hook_line(hook: dict) -> str:
    return (
        f"- Evidence: {hook.get('evidence', '')}\n"
        f"  Relevance: {hook.get('relevance', '')}\n"
        f"  Outreach angle: {hook.get('outreach_angle', '')}"
    )


def to_markdown(brief: dict) -> str:
    lines = [f"# Prospect Brief: {brief.get('prospect_name', 'Unknown')}", ""]

    for key, title in CLAIM_SECTION_TITLES.items():
        claims = brief.get(key) or []
        if not claims:
            continue
        lines.append(f"## {title}")
        for claim in claims:
            lines.append(_claim_line(claim))
        lines.append("")

    career_timeline = brief.get("career_timeline") or []
    if career_timeline:
        lines.append("## Career Timeline")
        for entry in career_timeline:
            lines.append(_career_entry_line(entry))
        lines.append("")

    activity = brief.get("activity") or []
    if activity:
        lines.append("## Activity")
        for item in activity:
            lines.append(_activity_line(item))
        lines.append("")

    hooks = brief.get("personalization_hooks") or []
    if hooks:
        lines.append("## Personalisation Hooks")
        for hook in hooks:
            lines.append(_hook_line(hook))
        lines.append("")

    outreach = brief.get("outreach_strategy") or {}
    if any(outreach.get(k) for k in ("angle", "primary_hooks", "question_or_value_prop", "opening_approach", "avoid")):
        lines.append("## Outreach Strategy")
        if outreach.get("angle"):
            lines.append(f"- Angle: {outreach['angle']}")
        if outreach.get("question_or_value_prop"):
            lines.append(f"- Question / value prop: {outreach['question_or_value_prop']}")
        if outreach.get("opening_approach"):
            lines.append(f"- Opening approach: {outreach['opening_approach']}")
        for h in outreach.get("primary_hooks") or []:
            lines.append(f"- Primary hook: {h}")
        for a in outreach.get("avoid") or []:
            lines.append(f"- Avoid: {a}")
        lines.append("")

    research_gaps = brief.get("research_gaps") or {}
    gap_fields = [
        ("missing_information", "Missing Information"),
        ("limited_coverage_areas", "Limited Coverage Areas"),
        ("conflicting_information", "Conflicting Information"),
        ("unverified_claims", "Unverified Claims"),
        ("inaccessible_sources", "Inaccessible Sources"),
    ]
    if any(research_gaps.get(field) for field, _ in gap_fields):
        lines.append("## Research Gaps")
        for field, label in gap_fields:
            values = research_gaps.get(field) or []
            if not values:
                continue
            lines.append(f"**{label}:**")
            for v in values:
                lines.append(f"- {v}")
        lines.append("")

    sources = brief.get("sources") or []
    if sources:
        lines.append("## Sources")
        for s in sources:
            title = s.get("title") or s["url"]
            lines.append(f"- [{s['id']}] [{title}]({s['url']})")
        lines.append("")

    return "\n".join(lines)


def to_pdf(brief: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=LETTER)
    styles = getSampleStyleSheet()
    story = [Paragraph(f"Prospect Brief: {brief.get('prospect_name', 'Unknown')}", styles["Title"]), Spacer(1, 12)]

    for key, title in CLAIM_SECTION_TITLES.items():
        claims = brief.get(key) or []
        if not claims:
            continue
        story.append(Paragraph(title, styles["Heading2"]))
        for claim in claims:
            marker = " (inference)" if claim.get("is_inference") else ""
            date = f" ({claim['date']})" if claim.get("date") else ""
            story.append(Paragraph(f"&bull; {claim['text']}{marker}{date}", styles["BodyText"]))
        story.append(Spacer(1, 8))

    career_timeline = brief.get("career_timeline") or []
    if career_timeline:
        story.append(Paragraph("Career Timeline", styles["Heading2"]))
        for entry in career_timeline:
            dates = f"{entry.get('start_date') or '?'} - {entry.get('end_date') or 'present'}"
            desc = f" — {entry['description']}" if entry.get("description") else ""
            story.append(
                Paragraph(
                    f"&bull; {entry.get('title', '')} at {entry.get('organization', '')} ({dates}){desc}",
                    styles["BodyText"],
                )
            )
        story.append(Spacer(1, 8))

    activity = brief.get("activity") or []
    if activity:
        story.append(Paragraph("Activity", styles["Heading2"]))
        for item in activity:
            activity_type = (item.get("activity_type") or "").replace("_", " ")
            published = f" ({item['published_at']})" if item.get("published_at") else ""
            url = item.get("url") or ""
            story.append(
                Paragraph(
                    f"&bull; [{activity_type}] {item.get('topic', '')}{published} {url}",
                    styles["BodyText"],
                )
            )
        story.append(Spacer(1, 8))

    hooks = brief.get("personalization_hooks") or []
    if hooks:
        story.append(Paragraph("Personalisation Hooks", styles["Heading2"]))
        for hook in hooks:
            story.append(
                Paragraph(
                    f"&bull; Evidence: {hook.get('evidence', '')} | Relevance: {hook.get('relevance', '')} "
                    f"| Outreach angle: {hook.get('outreach_angle', '')}",
                    styles["BodyText"],
                )
            )
        story.append(Spacer(1, 8))

    outreach = brief.get("outreach_strategy") or {}
    if any(outreach.get(k) for k in ("angle", "primary_hooks", "question_or_value_prop", "opening_approach", "avoid")):
        story.append(Paragraph("Outreach Strategy", styles["Heading2"]))
        if outreach.get("angle"):
            story.append(Paragraph(f"&bull; Angle: {outreach['angle']}", styles["BodyText"]))
        if outreach.get("question_or_value_prop"):
            story.append(
                Paragraph(
                    f"&bull; Question / value prop: {outreach['question_or_value_prop']}", styles["BodyText"]
                )
            )
        if outreach.get("opening_approach"):
            story.append(
                Paragraph(f"&bull; Opening approach: {outreach['opening_approach']}", styles["BodyText"])
            )
        for h in outreach.get("primary_hooks") or []:
            story.append(Paragraph(f"&bull; Primary hook: {h}", styles["BodyText"]))
        for a in outreach.get("avoid") or []:
            story.append(Paragraph(f"&bull; Avoid: {a}", styles["BodyText"]))
        story.append(Spacer(1, 8))

    research_gaps = brief.get("research_gaps") or {}
    gap_fields = [
        ("missing_information", "Missing Information"),
        ("limited_coverage_areas", "Limited Coverage Areas"),
        ("conflicting_information", "Conflicting Information"),
        ("unverified_claims", "Unverified Claims"),
        ("inaccessible_sources", "Inaccessible Sources"),
    ]
    if any(research_gaps.get(field) for field, _ in gap_fields):
        story.append(Paragraph("Research Gaps", styles["Heading2"]))
        for field, label in gap_fields:
            values = research_gaps.get(field) or []
            for v in values:
                story.append(Paragraph(f"&bull; {label}: {v}", styles["BodyText"]))
        story.append(Spacer(1, 8))

    sources = brief.get("sources") or []
    if sources:
        story.append(Paragraph("Sources", styles["Heading2"]))
        for s in sources:
            label = s.get("title") or s["url"]
            story.append(Paragraph(f"[{s['id']}] {label} — {s['url']}", styles["BodyText"]))

    doc.build(story)
    return buf.getvalue()
