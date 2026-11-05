from app.services.qa_sync import draft_email, score_confidence


def test_score_confidence_high_when_everything_checks_out():
    result = score_confidence(True, ["valid"], "completed")

    assert result["level"] == "high"
    assert result["needs_review"] is False


def test_score_confidence_low_when_nothing_confirmed():
    result = score_confidence(False, [], None)

    assert result["level"] == "low"
    assert result["needs_review"] is True


def test_score_confidence_medium_with_partial_signals():
    result = score_confidence(True, ["needs_review"], None)

    assert result["level"] == "medium"
    assert result["needs_review"] is False


def test_draft_email_uses_personalization_hook_when_present():
    brief_data = {
        "personalization_hooks": [{"evidence": "their recent Series B announcement"}],
        "outreach_strategy": {},
    }

    draft = draft_email("Jane Doe", "GenAI Accelerator", brief_data)

    assert "Jane" in draft["subject"]
    assert "Series B announcement" in draft["body"]


def test_draft_email_falls_back_to_generic_opening_without_hooks():
    draft = draft_email("Jane Doe", "GenAI Accelerator", {})

    assert "wanted to reach out" in draft["body"]
    assert "fabricat" not in draft["body"].lower()
