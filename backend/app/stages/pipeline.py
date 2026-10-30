import asyncio

from app.stages.base import Stage, StageContext, StageName, StageResult


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

    async def _run_stage(self, ctx: StageContext, name: StageName) -> StageResult:
        stage = self.stages[name]
        try:
            result = await stage.run(ctx)
        except Exception as exc:  # noqa: BLE001 - re-raised as a typed pipeline error
            raise StageFailedError(name, exc) from exc
        ctx.outputs[name.value] = result.output
        ctx.outputs[f"_sources_{name.value}"] = result.sources
        return result

    async def run(self, ctx: StageContext) -> dict[StageName, StageResult]:
        results: dict[StageName, StageResult] = {}

        results[StageName.RESOLVE_IDENTITY] = await self._run_stage(
            ctx, StageName.RESOLVE_IDENTITY
        )
        results[StageName.FETCH_PROFILE] = await self._run_stage(ctx, StageName.FETCH_PROFILE)

        parallel_names = [n for n in PARALLEL_AFTER_FETCH if n in self.stages]
        parallel_results = await asyncio.gather(
            *(self._run_stage(ctx, name) for name in parallel_names)
        )
        for name, result in zip(parallel_names, parallel_results):
            results[name] = result

        results[StageName.SYNTHESISE_BRIEF] = await self._run_stage(
            ctx, StageName.SYNTHESISE_BRIEF
        )
        return results
