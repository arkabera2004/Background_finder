"""Deterministic keyword heuristic for classifying public activity items.

No AI call — this is a cheap, exact rule-based classifier that never raises,
even on empty or non-English text. It intentionally errs toward the
conservative default (`OTHER_PUBLIC_ACTIVITY`) rather than guessing.
"""

from app.schemas.brief import ActivityType


def classify_activity(text: str, is_known_repost: bool | None = None) -> ActivityType:
    """Classify a piece of text (post, article title+snippet, etc.) into one
    of the 8 `ActivityType` values.

    `is_known_repost=True` short-circuits to `REPOST_OR_SHARE` regardless of
    text content, since the caller already knows this from structured data
    (e.g. `Post.is_repost`). Falls through to `OTHER_PUBLIC_ACTIVITY` for
    empty/non-English/unrecognized text — never raises.
    """
    if is_known_repost:
        return ActivityType.REPOST_OR_SHARE

    lowered = (text or "").lower()

    if "podcast" in lowered or "interview" in lowered:
        return ActivityType.INTERVIEW_OR_PODCAST
    if "talk" in lowered or "webinar" in lowered or "conference" in lowered:
        return ActivityType.TALK_OR_PRESENTATION
    if "announc" in lowered:
        return ActivityType.PROFESSIONAL_ANNOUNCEMENT
    if "article" in lowered or "publication" in lowered or "published" in lowered:
        return ActivityType.ARTICLE_OR_PUBLICATION
    if "comment" in lowered:
        return ActivityType.COMMENT
    if "repost" in lowered or "shared" in lowered or "re-share" in lowered:
        return ActivityType.REPOST_OR_SHARE

    return ActivityType.OTHER_PUBLIC_ACTIVITY


def is_byline_match(name: str, text: str) -> bool:
    """Simple heuristic: does `name` appear as byline-like text near the
    start of `text` (e.g. a title or snippet)? Used to decide whether a
    search-discovered article/interview can be attributed to the person
    (`authored_by_person=True`) rather than merely mentioning them.
    """
    if not name or not text:
        return False
    prefix = text[: len(name) + 40].lower()
    return name.lower() in prefix
