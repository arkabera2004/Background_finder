import asyncio
from typing import Callable

from app.stages.base import Stage, StageContext, StageName, StageResult

StageHook = Callable[[StageName, str], None]  # (stage, "started"|"completed"|"failed")


class StageFailedError(Exception):
    def __init__(self, stage: StageName, cause: Exception):
        self.stage = stage
        self.cause = cause
        super().__init__(f"Stage {stage.value} failed: {cause}")


# fetch_profile must finish before these three; they run concurrently.
PARALLEL_AFTER_FETCH = (
    StageName.ANALYSE_CAREER,
    StageName.RESEARCH_COMPANY,
    StageName.ANALYSE_ACTIVITY,
    StageName.WEB_FOOTPRINT,
)


class Pipeline:
    """Runs the seven research stages in the required dependency order.

    resolve_identity -> fetch_profile -> {analyse_career, research_company,
    analyse_activity, web_footprint} (concurrent) -> synthesise_brief.
    """

    def __init__(self, stages: dict[StageName, Stage]):
        missing = {
            StageName.RESOLVE_IDENTITY,
            StageName.FETCH_PROFILE,
            StageName.SYNTHESISE_BRIEF,
        } - stages.keys()
        if missing:
            raise ValueError(f"Pipeline missing required stages: {missing}")
        self.stages = stages

    async def _run_stage(
        self, ctx: StageContext, name: StageName, on_event: StageHook | None
    ) -> StageResult:
        stage = self.stages[name]
        if on_event:
            on_event(name, "started")
        try:
            result = await stage.run(ctx)
        except Exception as exc:  # noqa: BLE001 - re-raised as a typed pipeline error
            if on_event:
                on_event(name, "failed")
            raise StageFailedError(name, exc) from exc
        ctx.outputs[name.value] = result.output
        ctx.outputs[f"_sources_{name.value}"] = result.sources
        if on_event:
            on_event(name, "completed")
        return result

    async def run(
        self, ctx: StageContext, on_event: StageHook | None = None
    ) -> dict[StageName, StageResult]:
        results: dict[StageName, StageResult] = {}

        results[StageName.RESOLVE_IDENTITY] = await self._run_stage(
            ctx, StageName.RESOLVE_IDENTITY, on_event
        )
        results[StageName.FETCH_PROFILE] = await self._run_stage(
            ctx, StageName.FETCH_PROFILE, on_event
        )

        # A failure in any one of these (e.g. company research can't reach a
        # provider) must not destroy data already gathered by the others, so
        # exceptions are collected rather than propagated.
        parallel_names = [n for n in PARALLEL_AFTER_FETCH if n in self.stages]
        parallel_results = await asyncio.gather(
            *(self._run_stage(ctx, name, on_event) for name in parallel_names),
            return_exceptions=True,
        )
        for name, result in zip(parallel_names, parallel_results):
            if isinstance(result, BaseException):
                ctx.stage_failures[name] = result
                continue
            results[name] = result

        results[StageName.SYNTHESISE_BRIEF] = await self._run_stage(
            ctx, StageName.SYNTHESISE_BRIEF, on_event
        )
        return results
