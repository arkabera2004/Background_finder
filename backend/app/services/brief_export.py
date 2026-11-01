import io
import json

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

# Claim-list sections: rendered as a bulleted list of Claim objects
# ({"text", "is_inference", "confidence", "source_ids", "date"}).
CLAIM_SECTION_TITLES = {
    "snapshot": "Executive Overview",
    "current_role": "Current Role & Responsibilities",
    "company_overview": "Company Overview",
    "expertise": "Expertise",
    "recurring_themes": "Recurring Themes",
    "company_context": "Company Context",
    "communication_style": "Communication Style",
    "likely_priorities": "Likely Priorities",
}

SECTION_TITLES = CLAIM_SECTION_TITLES  # backwards-compatible alias

# Section 10/11 split activity by type per the person-centric research spec.
PUBLICATION_ACTIVITY_TYPES = {"article_or_publication", "interview_or_podcast", "talk_or_presentation"}


def to_json(brief: dict) -> str:
    return json.dumps(brief, indent=2, default=str)


def _claim_line(claim: dict) -> str:
    marker = " _(inference)_" if claim.get("is_inference") else ""
    date = f" ({claim['date']})" if claim.get("date") else ""
    return f"- {claim['text']}{marker}{date} [{claim.get('confidence', 'medium')}]"


def _career_entry_line(entry: dict) -> str:
    dates = f"{entry.get('start_date') or '?'} – {entry.get('end_date') or 'present'}"
    precision = entry.get("date_precision") or "unknown"
    line = f"- **{entry.get('title', '')}** at **{entry.get('organization', '')}** ({dates}, dates {precision})"
    if entry.get("description"):
        line += f" — {entry['description']}"
    return line


def _education_line(entry: dict) -> str:
    degree = f"{entry['degree']} " if entry.get("degree") else ""
    field = f"in {entry['field']} " if entry.get("field") else ""
    dates = f"{entry.get('start_date') or '?'} – {entry.get('end_date') or '?'}"
    return f"- {degree}{field}at **{entry.get('institution', '')}** ({dates})"


def _company_profile_block(entry: dict) -> list[str]:
    lines = [f"### {entry.get('name', 'Unknown')}"]
    if entry.get("website"):
        lines.append(f"- Website: {entry['website']}")
    if entry.get("what_they_do"):
        lines.append(f"- What they do: {entry['what_they_do']}")
    if entry.get("industry"):
        lines.append(f"- Industry: {entry['industry']}")
    dates = f"{entry.get('start_date') or '?'} – {entry.get('end_date') or 'present'}"
    lines.append(f"- Role: {entry.get('person_role', '')} ({dates}, dates {entry.get('date_precision', 'unknown')})")
    if entry.get("role_scope"):
        lines.append(f"- Scope: {entry['role_scope']}")
    for p in entry.get("related_projects") or []:
        lines.append(f"- Related project: {p}")
    if entry.get("uncertainty_note"):
        lines.append(f"- _Note: {entry['uncertainty_note']}_")
    return lines


def _activity_line(item: dict) -> str:
    activity_type = (item.get("activity_type") or "").replace("_", " ")
    published = f" ({item['published_at']})" if item.get("published_at") else ""
    url = item.get("url") or ""
    url_part = f" — [{url}]({url})" if url else ""
    authored = "" if item.get("authored_by_person", True) else " _(not authored by this person)_"
    return f"- [{activity_type}] {item.get('topic', '')}{published}{authored}{url_part}"


def _hook_line(hook: dict) -> str:
    return (
        f"- Evidence: {hook.get('evidence', '')}\n"
        f"  Relevance: {hook.get('relevance', '')}\n"
        f"  Outreach angle: {hook.get('outreach_angle', '')}"
    )


def _same_name_block(entry: dict) -> list[str]:
    lines = [f"- **{entry.get('name', 'Unknown')}** — {entry.get('identity_summary', '')}"]
    if entry.get("distinguishing_info"):
        lines.append(f"  - {entry['distinguishing_info']}")
    lines.append(f"  - Why confusable: {entry.get('why_confusable', '')}")
    lines.append(f"  - Why different: {entry.get('why_different', '')}")
    return lines


def _related_personality_line(entry: dict) -> str:
    role = f", {entry['role']}" if entry.get("role") else ""
    return (
        f"- **{entry.get('name', 'Unknown')}**{role} — {entry.get('connection_type', '')} "
        f"({entry.get('strength', 'possible')}). {entry.get('evidence', '')}"
    )


def to_markdown(brief: dict) -> str:
    lines = [f"# Prospect Brief: {brief.get('prospect_name', 'Unknown')}", ""]

    # 1. Identity Verification
    identity = brief.get("identity_verification")
    if identity:
        lines.append("## Identity Verification")
        if identity.get("profile_url"):
            lines.append(f"- Profile used: {identity['profile_url']}")
        for ident in identity.get("matched_identifiers") or []:
            lines.append(f"- Matched: {ident}")
        lines.append(f"- Confidence: {identity.get('confidence', 'medium')}")
        if identity.get("limitations"):
            lines.append(f"- Limitations: {identity['limitations']}")
        lines.append("")

    # 2. Executive Overview
    snapshot = brief.get("snapshot") or []
    if snapshot:
        lines.append("## Executive Overview")
        for claim in snapshot:
            lines.append(_claim_line(claim))
        lines.append("")

    # 3. Detailed Person Summary
    detailed_summary = brief.get("detailed_summary") or []
    if detailed_summary:
        lines.append("## Detailed Person Summary")
        for claim in detailed_summary:
            lines.append(_claim_line(claim))
        lines.append("")

    # 4. Education & Early Background
    education = brief.get("education") or []
    lines.append("## Education & Early Background")
    if education:
        for entry in education:
            lines.append(_education_line(entry))
    else:
        lines.append("_No publicly documented education history was found._")
    lines.append("")

    # 5. Complete Career Timeline
    career_timeline = brief.get("career_timeline") or []
    if career_timeline:
        lines.append("## Complete Career Timeline")
        for entry in career_timeline:
            lines.append(_career_entry_line(entry))
        lines.append("")

    # 6. Company-by-Company Overview
    company_profiles = brief.get("company_profiles") or []
    if company_profiles:
        lines.append("## Company-by-Company Overview")
        for entry in company_profiles:
            lines.extend(_company_profile_block(entry))
            lines.append("")

    # 7. Current Role & Responsibilities
    current_role = brief.get("current_role") or []
    if current_role:
        lines.append("## Current Role & Responsibilities")
        for claim in current_role:
            lines.append(_claim_line(claim))
        lines.append("")

    # 8. Achievements & Milestones
    achievements = brief.get("achievements") or []
    lines.append("## Achievements & Milestones")
    if achievements:
        for claim in achievements:
            lines.append(_claim_line(claim))
    else:
        lines.append("_No independently verifiable achievements were found._")
    lines.append("")

    # 9. Research, Expertise & Professional Interests
    expertise = brief.get("expertise") or []
    recurring_themes = brief.get("recurring_themes") or []
    if expertise or recurring_themes:
        lines.append("## Research, Expertise & Professional Interests")
        for claim in expertise:
            lines.append(_claim_line(claim))
        for claim in recurring_themes:
            lines.append(_claim_line(claim))
        lines.append("")

    company_context = brief.get("company_context") or []
    if company_context:
        lines.append("## Company Context")
        for claim in company_context:
            lines.append(_claim_line(claim))
        lines.append("")

    communication_style = brief.get("communication_style") or []
    if communication_style:
        lines.append("## Communication Style")
        for claim in communication_style:
            lines.append(_claim_line(claim))
        lines.append("")

    likely_priorities = brief.get("likely_priorities") or []
    if likely_priorities:
        lines.append("## Likely Priorities")
        for claim in likely_priorities:
            lines.append(_claim_line(claim))
        lines.append("")

    # 10 & 11. Posts/Activity, split from Publications/Talks/Interviews
    activity = brief.get("activity") or []
    posts = [a for a in activity if (a.get("activity_type") or "") not in PUBLICATION_ACTIVITY_TYPES]
    publications = [a for a in activity if (a.get("activity_type") or "") in PUBLICATION_ACTIVITY_TYPES]

    lines.append("## Posts, Reposts & Public Activity")
    if posts:
        for item in posts:
            lines.append(_activity_line(item))
    else:
        lines.append("_No public posts or reposts were accessible for this person._")
    lines.append("")

    lines.append("## Publications, Talks & Interviews")
    if publications:
        for item in publications:
            lines.append(_activity_line(item))
    else:
        lines.append("_No publications, talks, or interviews were found._")
    lines.append("")

    # 12. People with the Same Name
    same_name_people = brief.get("same_name_people") or []
    lines.append("## People with the Same Name")
    if same_name_people:
        for entry in same_name_people:
            lines.extend(_same_name_block(entry))
    else:
        lines.append("_No meaningful same-name matches were found._")
    lines.append("")

    # 13. Related Personalities
    related_personalities = brief.get("related_personalities") or []
    lines.append("## Related Personalities")
    if related_personalities:
        for entry in related_personalities:
            lines.append(_related_personality_line(entry))
    else:
        lines.append("_No demonstrably connected personalities were found._")
    lines.append("")

    # 14. Common Ground & Conversation Opportunities
    hooks = brief.get("personalization_hooks") or []
    if hooks:
        lines.append("## Common Ground & Conversation Opportunities")
        for hook in hooks:
            lines.append(_hook_line(hook))
        lines.append("")

    # 15. Personalized Outreach Brief
    outreach = brief.get("outreach_strategy") or {}
    if any(outreach.get(k) for k in ("angle", "primary_hooks", "question_or_value_prop", "opening_approach", "avoid")):
        lines.append("## Personalized Outreach Brief")
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

    # 16. Sources & Evidence
    sources = brief.get("sources") or []
    if sources:
        lines.append("## Sources & Evidence")
        for s in sources:
            title = s.get("title") or s["url"]
            lines.append(f"- [{s['id']}] [{title}]({s['url']})")
        lines.append("")

    # 17. Research Gaps, Conflicts & Limitations
    research_gaps = brief.get("research_gaps") or {}
    gap_fields = [
        ("missing_information", "Missing Information"),
        ("limited_coverage_areas", "Limited Coverage Areas"),
        ("conflicting_information", "Conflicting Information"),
        ("unverified_claims", "Unverified Claims"),
        ("inaccessible_sources", "Inaccessible Sources"),
    ]
    if any(research_gaps.get(field) for field, _ in gap_fields):
        lines.append("## Research Gaps, Conflicts & Limitations")
        for field, label in gap_fields:
            values = research_gaps.get(field) or []
            if not values:
                continue
            lines.append(f"**{label}:**")
            for v in values:
                lines.append(f"- {v}")
        lines.append("")

    return "\n".join(lines)


def _pdf_claims(story: list, styles, title: str, claims: list[dict]) -> None:
    story.append(Paragraph(title, styles["Heading2"]))
    for claim in claims:
        marker = " (inference)" if claim.get("is_inference") else ""
        date = f" ({claim['date']})" if claim.get("date") else ""
        story.append(Paragraph(f"&bull; {claim['text']}{marker}{date}", styles["BodyText"]))
    story.append(Spacer(1, 8))


def to_pdf(brief: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=LETTER)
    styles = getSampleStyleSheet()
    story = [Paragraph(f"Prospect Brief: {brief.get('prospect_name', 'Unknown')}", styles["Title"]), Spacer(1, 12)]

    identity = brief.get("identity_verification")
    if identity:
        story.append(Paragraph("Identity Verification", styles["Heading2"]))
        if identity.get("profile_url"):
            story.append(Paragraph(f"&bull; Profile used: {identity['profile_url']}", styles["BodyText"]))
        for ident in identity.get("matched_identifiers") or []:
            story.append(Paragraph(f"&bull; Matched: {ident}", styles["BodyText"]))
        story.append(
            Paragraph(f"&bull; Confidence: {identity.get('confidence', 'medium')}", styles["BodyText"])
        )
        if identity.get("limitations"):
            story.append(Paragraph(f"&bull; Limitations: {identity['limitations']}", styles["BodyText"]))
        story.append(Spacer(1, 8))

    if brief.get("snapshot"):
        _pdf_claims(story, styles, "Executive Overview", brief["snapshot"])

    if brief.get("detailed_summary"):
        _pdf_claims(story, styles, "Detailed Person Summary", brief["detailed_summary"])

    education = brief.get("education") or []
    story.append(Paragraph("Education & Early Background", styles["Heading2"]))
    if education:
        for entry in education:
            degree = f"{entry['degree']} " if entry.get("degree") else ""
            field = f"in {entry['field']} " if entry.get("field") else ""
            dates = f"{entry.get('start_date') or '?'} - {entry.get('end_date') or '?'}"
            story.append(
                Paragraph(
                    f"&bull; {degree}{field}at {entry.get('institution', '')} ({dates})", styles["BodyText"]
                )
            )
    else:
        story.append(Paragraph("No publicly documented education history was found.", styles["BodyText"]))
    story.append(Spacer(1, 8))

    career_timeline = brief.get("career_timeline") or []
    if career_timeline:
        story.append(Paragraph("Complete Career Timeline", styles["Heading2"]))
        for entry in career_timeline:
            dates = f"{entry.get('start_date') or '?'} - {entry.get('end_date') or 'present'}"
            desc = f" — {entry['description']}" if entry.get("description") else ""
            story.append(
                Paragraph(
                    f"&bull; {entry.get('title', '')} at {entry.get('organization', '')} "
                    f"({dates}, dates {entry.get('date_precision', 'unknown')}){desc}",
                    styles["BodyText"],
                )
            )
        story.append(Spacer(1, 8))

    company_profiles = brief.get("company_profiles") or []
    if company_profiles:
        story.append(Paragraph("Company-by-Company Overview", styles["Heading2"]))
        for entry in company_profiles:
            dates = f"{entry.get('start_date') or '?'} - {entry.get('end_date') or 'present'}"
            what = f" — {entry['what_they_do']}" if entry.get("what_they_do") else ""
            story.append(
                Paragraph(
                    f"&bull; <b>{entry.get('name', '')}</b>{what}: {entry.get('person_role', '')} ({dates})",
                    styles["BodyText"],
                )
            )
            if entry.get("uncertainty_note"):
                story.append(Paragraph(f"&nbsp;&nbsp;Note: {entry['uncertainty_note']}", styles["BodyText"]))
        story.append(Spacer(1, 8))

    if brief.get("current_role"):
        _pdf_claims(story, styles, "Current Role & Responsibilities", brief["current_role"])

    achievements = brief.get("achievements") or []
    story.append(Paragraph("Achievements & Milestones", styles["Heading2"]))
    if achievements:
        for claim in achievements:
            story.append(Paragraph(f"&bull; {claim['text']}", styles["BodyText"]))
    else:
        story.append(Paragraph("No independently verifiable achievements were found.", styles["BodyText"]))
    story.append(Spacer(1, 8))

    expertise_themes = (brief.get("expertise") or []) + (brief.get("recurring_themes") or [])
    if expertise_themes:
        _pdf_claims(story, styles, "Research, Expertise & Professional Interests", expertise_themes)

    if brief.get("company_context"):
        _pdf_claims(story, styles, "Company Context", brief["company_context"])
    if brief.get("communication_style"):
        _pdf_claims(story, styles, "Communication Style", brief["communication_style"])
    if brief.get("likely_priorities"):
        _pdf_claims(story, styles, "Likely Priorities", brief["likely_priorities"])

    activity = brief.get("activity") or []
    posts = [a for a in activity if (a.get("activity_type") or "") not in PUBLICATION_ACTIVITY_TYPES]
    publications = [a for a in activity if (a.get("activity_type") or "") in PUBLICATION_ACTIVITY_TYPES]

    story.append(Paragraph("Posts, Reposts & Public Activity", styles["Heading2"]))
    if posts:
        for item in posts:
            activity_type = (item.get("activity_type") or "").replace("_", " ")
            published = f" ({item['published_at']})" if item.get("published_at") else ""
            url = item.get("url") or ""
            story.append(
                Paragraph(
                    f"&bull; [{activity_type}] {item.get('topic', '')}{published} {url}", styles["BodyText"]
                )
            )
    else:
        story.append(Paragraph("No public posts or reposts were accessible for this person.", styles["BodyText"]))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Publications, Talks & Interviews", styles["Heading2"]))
    if publications:
        for item in publications:
            activity_type = (item.get("activity_type") or "").replace("_", " ")
            published = f" ({item['published_at']})" if item.get("published_at") else ""
            url = item.get("url") or ""
            story.append(
                Paragraph(
                    f"&bull; [{activity_type}] {item.get('topic', '')}{published} {url}", styles["BodyText"]
                )
            )
    else:
        story.append(Paragraph("No publications, talks, or interviews were found.", styles["BodyText"]))
    story.append(Spacer(1, 8))

    same_name_people = brief.get("same_name_people") or []
    story.append(Paragraph("People with the Same Name", styles["Heading2"]))
    if same_name_people:
        for entry in same_name_people:
            story.append(
                Paragraph(
                    f"&bull; <b>{entry.get('name', '')}</b> — {entry.get('identity_summary', '')}. "
                    f"Why different: {entry.get('why_different', '')}",
                    styles["BodyText"],
                )
            )
    else:
        story.append(Paragraph("No meaningful same-name matches were found.", styles["BodyText"]))
    story.append(Spacer(1, 8))

    related_personalities = brief.get("related_personalities") or []
    story.append(Paragraph("Related Personalities", styles["Heading2"]))
    if related_personalities:
        for entry in related_personalities:
            role = f", {entry['role']}" if entry.get("role") else ""
            story.append(
                Paragraph(
                    f"&bull; <b>{entry.get('name', '')}</b>{role} — {entry.get('connection_type', '')} "
                    f"({entry.get('strength', 'possible')})",
                    styles["BodyText"],
                )
            )
    else:
        story.append(Paragraph("No demonstrably connected personalities were found.", styles["BodyText"]))
    story.append(Spacer(1, 8))

    hooks = brief.get("personalization_hooks") or []
    if hooks:
        story.append(Paragraph("Common Ground & Conversation Opportunities", styles["Heading2"]))
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
        story.append(Paragraph("Personalized Outreach Brief", styles["Heading2"]))
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

    sources = brief.get("sources") or []
    if sources:
        story.append(Paragraph("Sources & Evidence", styles["Heading2"]))
        for s in sources:
            label = s.get("title") or s["url"]
            story.append(Paragraph(f"[{s['id']}] {label} — {s['url']}", styles["BodyText"]))
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
        story.append(Paragraph("Research Gaps, Conflicts & Limitations", styles["Heading2"]))
        for field, label in gap_fields:
            values = research_gaps.get(field) or []
            for v in values:
                story.append(Paragraph(f"&bull; {label}: {v}", styles["BodyText"]))

    doc.build(story)
    return buf.getvalue()
