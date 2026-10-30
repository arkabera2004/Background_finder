import io
import json

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

SECTION_TITLES = {
    "snapshot": "Snapshot",
    "career_story": "Career Story",
    "current_role": "Current Role",
    "company": "Company",
    "content_and_interests": "Content & Interests",
    "communication_style": "Communication Style",
    "likely_priorities": "Likely Priorities",
}


def to_json(brief: dict) -> str:
    return json.dumps(brief, indent=2, default=str)


def to_markdown(brief: dict) -> str:
    lines = [f"# Prospect Brief: {brief.get('prospect_name', 'Unknown')}", ""]

    for key, title in SECTION_TITLES.items():
        claims = brief.get(key) or []
        if not claims:
            continue
        lines.append(f"## {title}")
        for claim in claims:
            marker = " _(inference)_" if claim.get("is_inference") else ""
            lines.append(f"- {claim['text']}{marker} [{claim.get('confidence', 'medium')}]")
        lines.append("")

    hooks = brief.get("hooks") or []
    if hooks:
        lines.append("## Personalisation Hooks")
        for hook in hooks:
            lines.append(f"- {hook['text']}")
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

    for key, title in SECTION_TITLES.items():
        claims = brief.get(key) or []
        if not claims:
            continue
        story.append(Paragraph(title, styles["Heading2"]))
        for claim in claims:
            marker = " (inference)" if claim.get("is_inference") else ""
            story.append(Paragraph(f"&bull; {claim['text']}{marker}", styles["BodyText"]))
        story.append(Spacer(1, 8))

    sources = brief.get("sources") or []
    if sources:
        story.append(Paragraph("Sources", styles["Heading2"]))
        for s in sources:
            label = s.get("title") or s["url"]
            story.append(Paragraph(f"[{s['id']}] {label} — {s['url']}", styles["BodyText"]))

    doc.build(story)
    return buf.getvalue()
