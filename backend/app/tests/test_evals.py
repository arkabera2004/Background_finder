import pytest

from app.evals.fixtures import FIXTURES
from app.evals.run_eval import run_evaluation


def test_fixture_set_has_20_unique_synthetic_profiles():
    assert len(FIXTURES) == 20
    assert len({f.expected_name for f in FIXTURES}) == 20


@pytest.mark.asyncio
async def test_offline_eval_run_produces_real_measured_results():
    result = await run_evaluation(use_live_providers=False)

    assert result.total == 20
    # Manual mode trusts the submitted identity directly, so this must be
    # exactly 100% — if it's ever less, that's a real regression.
    assert result.identity_resolution_accuracy == 1.0
    # Every claim the rule-based synthesiser produces must be sourced or
    # explicitly marked an inference — the citation validator enforces this.
    assert result.citation_coverage == 1.0
    assert result.sensitive_leaks == []
