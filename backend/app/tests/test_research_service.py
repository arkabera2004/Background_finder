import pytest

from app.services.research_service import create_run, execute_run


@pytest.mark.asyncio
async def test_execute_run_completes_in_manual_mode():
    run = create_run(
        owner_id="user-1",
        depth="standard",
        full_name="Jane Doe",
        linkedin_url=None,
        company=None,
        pasted_text="Jane Doe\nSenior Engineer at Acme\nBuilds reliable systems.",
    )
    await execute_run(run)

    assert run.status == "completed"
    assert run.brief["prospect_name"] == "Jane Doe"
    assert all(step.status == "completed" for step in run.steps.values())
    assert run.completed_at is not None


@pytest.mark.asyncio
async def test_execute_run_fails_cleanly_without_pasted_text_or_provider():
    run = create_run(
        owner_id="user-1",
        depth="standard",
        full_name="Jane Doe",
        linkedin_url="https://linkedin.com/in/jane-doe",
        company=None,
        pasted_text=None,
    )
    await execute_run(run)

    assert run.status == "failed"
    assert run.steps["fetch_profile"].status == "failed"
    assert run.steps["fetch_profile"].error is not None


@pytest.mark.asyncio
async def test_execute_run_respects_cancellation():
    run = create_run(
        owner_id="user-1",
        depth="standard",
        full_name="Jane Doe",
        linkedin_url=None,
        company=None,
        pasted_text="Jane Doe\nEngineer",
    )
    run.cancel_requested = True
    await execute_run(run)

    assert run.status == "cancelled"
