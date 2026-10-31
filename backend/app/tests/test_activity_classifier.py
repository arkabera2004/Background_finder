from app.schemas.brief import ActivityType
from app.services.activity_classifier import classify_activity, is_byline_match


class TestClassifyActivity:
    def test_interview_or_podcast(self) -> None:
        assert classify_activity("Listen to my new podcast episode") == (
            ActivityType.INTERVIEW_OR_PODCAST
        )
        assert classify_activity("An interview with the CEO") == (
            ActivityType.INTERVIEW_OR_PODCAST
        )

    def test_talk_or_presentation(self) -> None:
        assert classify_activity("My talk at the conference") == (
            ActivityType.TALK_OR_PRESENTATION
        )
        assert classify_activity("Join our webinar next week") == (
            ActivityType.TALK_OR_PRESENTATION
        )

    def test_professional_announcement(self) -> None:
        assert classify_activity("Excited to announce my new role") == (
            ActivityType.PROFESSIONAL_ANNOUNCEMENT
        )

    def test_article_or_publication(self) -> None:
        assert classify_activity("Read my latest article on AI") == (
            ActivityType.ARTICLE_OR_PUBLICATION
        )
        assert classify_activity("New publication out now") == (
            ActivityType.ARTICLE_OR_PUBLICATION
        )

    def test_comment(self) -> None:
        assert classify_activity("Great comment thread on this post") == ActivityType.COMMENT

    def test_repost_or_share_from_text(self) -> None:
        assert classify_activity("I reposted this great insight") == (
            ActivityType.REPOST_OR_SHARE
        )

    def test_repost_or_share_from_known_flag(self) -> None:
        assert classify_activity("totally unrelated text", is_known_repost=True) == (
            ActivityType.REPOST_OR_SHARE
        )
        # Known-repost flag wins even when text would otherwise classify
        # differently.
        assert classify_activity("my podcast episode", is_known_repost=True) == (
            ActivityType.REPOST_OR_SHARE
        )

    def test_original_post_is_not_directly_detectable_defaults_other(self) -> None:
        # ORIGINAL_POST has no keyword signal of its own in free text; callers
        # determine it from structured context (e.g. Post.is_repost is
        # False), not from this heuristic. Plain text with no other keyword
        # falls through to the default.
        assert classify_activity("Had a great day at work") == (
            ActivityType.OTHER_PUBLIC_ACTIVITY
        )

    def test_other_public_activity_default(self) -> None:
        assert classify_activity("") == ActivityType.OTHER_PUBLIC_ACTIVITY
        assert classify_activity("asdkjhasdkjh random text") == (
            ActivityType.OTHER_PUBLIC_ACTIVITY
        )

    def test_never_raises_on_empty_or_non_english_text(self) -> None:
        assert classify_activity("") == ActivityType.OTHER_PUBLIC_ACTIVITY
        assert classify_activity(None) == ActivityType.OTHER_PUBLIC_ACTIVITY  # type: ignore[arg-type]
        assert classify_activity("这是中文文本，没有关键词") == (
            ActivityType.OTHER_PUBLIC_ACTIVITY
        )


class TestIsBylineMatch:
    def test_name_near_start_matches(self) -> None:
        assert is_byline_match("Jane Doe", "Jane Doe: how I scaled my startup") is True

    def test_name_far_from_start_does_not_match(self) -> None:
        text = "x" * 100 + "Jane Doe was mentioned in passing"
        assert is_byline_match("Jane Doe", text) is False

    def test_empty_inputs_return_false(self) -> None:
        assert is_byline_match("", "some text") is False
        assert is_byline_match("Jane Doe", "") is False
