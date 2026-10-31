import asyncio
import time

import pytest

from app.stages.base import Stage, StageContext, StageName, StageResult
from app.stages.pipeline import Pipeline, StageFailedError


class RecordingStage(Stage):
    def __init__(self, name: StageName, log: list[str], delay: float = 0.0, fail: bool = False):
        self.name = name
        self._log = log
        self._delay = delay
        self._fail = fail

    async def run(self, ctx: StageContext) -> StageResult:
        if self._delay:
            await asyncio.sleep(self._delay)
        if self._fail:
            raise RuntimeError("boom")
        self._log.append(self.name.value)
        return StageResult(stage=self.name, output={"ran": self.name.value})


def make_pipeline(log: list[str], delay: float = 0.05) -> Pipeline:
    stages: dict[StageName, Stage] = {
        StageName.RESOLVE_IDENTITY: RecordingStage(StageName.RESOLVE_IDENTITY, log),
        StageName.FETCH_PROFILE: RecordingStage(StageName.FETCH_PROFILE, log),
        StageName.ANALYSE_CAREER: RecordingStage(StageName.ANALYSE_CAREER, log, delay=delay),
        StageName.RESEARCH_COMPANY: RecordingStage(StageName.RESEARCH_COMPANY, log, delay=delay),
        StageName.ANALYSE_ACTIVITY: RecordingStage(StageName.ANALYSE_ACTIVITY, log, delay=delay),
        StageName.WEB_FOOTPRINT: RecordingStage(StageName.WEB_FOOTPRINT, log, delay=delay),
        StageName.SYNTHESISE_BRIEF: RecordingStage(StageName.SYNTHESISE_BRIEF, log),
    }
    return Pipeline(stages)


@pytest.mark.asyncio
async def test_identity_and_fetch_run_before_everything_else():
    log: list[str] = []
    pipeline = make_pipeline(log)
    ctx = StageContext(run_id="run-1", depth="standard")

    await pipeline.run(ctx)

    assert log[0] == StageName.RESOLVE_IDENTITY.value
    assert log[1] == StageName.FETCH_PROFILE.value
    assert log[-1] == StageName.SYNTHESISE_BRIEF.value
    assert set(log[2:-1]) == {
        StageName.ANALYSE_CAREER.value,
        StageName.RESEARCH_COMPANY.value,
        StageName.ANALYSE_ACTIVITY.value,
        StageName.WEB_FOOTPRINT.value,
    }


@pytest.mark.asyncio
async def test_middle_stages_run_concurrently_not_sequentially():
    log: list[str] = []
    delay = 0.1
    pipeline = make_pipeline(log, delay=delay)
    ctx = StageContext(run_id="run-2", depth="standard")

    start = time.monotonic()
    await pipeline.run(ctx)
    elapsed = time.monotonic() - start

    # Sequential would take 4 * delay; concurrent should take ~1 * delay plus overhead.
    assert elapsed < delay * 2.5


@pytest.mark.asyncio
async def test_stage_failure_raises_typed_error():
    log: list[str] = []
    stages: dict[StageName, Stage] = {
        StageName.RESOLVE_IDENTITY: RecordingStage(StageName.RESOLVE_IDENTITY, log),
        StageName.FETCH_PROFILE: RecordingStage(StageName.FETCH_PROFILE, log, fail=True),
        StageName.SYNTHESISE_BRIEF: RecordingStage(StageName.SYNTHESISE_BRIEF, log),
    }
    pipeline = Pipeline(stages)
    ctx = StageContext(run_id="run-3", depth="standard")

    with pytest.raises(StageFailedError) as exc:
        await pipeline.run(ctx)
    assert exc.value.stage == StageName.FETCH_PROFILE


def test_pipeline_requires_core_stages():
    with pytest.raises(ValueError, match="missing required stages"):
        Pipeline({})
