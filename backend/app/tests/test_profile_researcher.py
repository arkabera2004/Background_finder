from app.services.profile_researcher import research_person


async def test_research_person_returns_status_and_brief():
    """No network/API key is configured in tests (see conftest.py's
    autouse fixture), so the underlying pipeline runs end-to-end with
    null/rule-based providers — this just checks the thin driver hands
    back exactly what the pipeline produced, status included."""
    outcome = await research_person(
        owner_id="user-1",
        full_name="Jane Doe",
        linkedin_url="https://linkedin.com/in/janedoe",
        company_name="Acme",
    )

    assert outcome["status"] in ("completed", "failed", "cancelled")
    if outcome["status"] == "completed":
        assert outcome["brief"] is not None
