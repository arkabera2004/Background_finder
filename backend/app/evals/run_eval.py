"""Evaluation runner. Reports MEASURED results against the 20 SYNTHETIC
fixtures in app/evals/fixtures.py — never estimated, never invented.

Run: PYTHONPATH=. .venv/bin/python -m app.evals.run_eval
"""

import asyncio
from dataclasses import dataclass, field

from app.core.config import settings
from app.evals.fixtures import FIXTURES
from app.services.research_service import create_run, execute_run

SENSITIVE_KEYWORDS = [
    "religion",
    "religious",
    "caste",
    "politic",
    "sexual",
    "sexuality",
    "disease",
    "illness",
    "pregnan",
    "disability",
]


@dataclass
class EvalResult:
    identity_resolution_correct: int = 0
    total: int = 0
    total_claims: int = 0
    sourced_or_inference_claims: int = 0
    total_hooks: int = 0
    sensitive_leaks: list[str] = field(default_factory=list)

    @property
    def identity_resolution_accuracy(self) -> float:
        return self.identity_resolution_correct / self.total if self.total else 0.0

    @property
    def citation_coverage(self) -> float:
        return self.sourced_or_inference_claims / self.total_claims if self.total_claims else 1.0

    @property
    def avg_hooks(self) -> float:
        return self.total_hooks / self.total if self.total else 0.0


def _scan_for_sensitive_content(text: str) -> list[str]:
    lowered = text.lower()
    return [kw for kw in SENSITIVE_KEYWORDS if kw in lowered]


async def run_evaluation(use_live_providers: bool = False) -> EvalResult:
    """By default, runs fully offline/deterministic (no search, no crawl) —
    this measures the manual-mode baseline, which is reproducible and
    doesn't depend on network conditions or rate limits. Pass
    use_live_providers=True to measure against real DuckDuckGo/local
    extraction instead (slower, not reproducible run-to-run)."""
    if not use_live_providers:
        settings.search_provider = "tavily"  # resolves to NullSearchProvider, no key
        settings.extraction_provider = "firecrawl"  # resolves to NullCrawler, no key

    result = EvalResult(total=len(FIXTURES))

    for fixture in FIXTURES:
        run = create_run(
            owner_id="eval-user",
            depth="standard",
            full_name=fixture.expected_name,
            linkedin_url=None,
            company=None,
            pasted_text=fixture.pasted_text,
        )
        await execute_run(run)

        if run.status != "completed" or run.brief is None:
            continue

        if run.brief.get("prospect_name") == fixture.expected_name:
            result.identity_resolution_correct += 1

        known_source_ids = {s["id"] for s in run.brief.get("sources", [])}
        for section in (
            "snapshot",
            "career_story",
            "current_role",
            "company",
            "content_and_interests",
            "communication_style",
            "likely_priorities",
        ):
            for claim in run.brief.get(section, []):
                result.total_claims += 1
                has_valid_source = any(
                    sid in known_source_ids for sid in claim.get("source_ids", [])
                )
                if claim.get("is_inference") or has_valid_source:
                    result.sourced_or_inference_claims += 1

                leaks = _scan_for_sensitive_content(claim.get("text", ""))
                if leaks:
                    result.sensitive_leaks.append(f"{fixture.id}: {leaks}")

        result.total_hooks += len(run.brief.get("hooks", []))

    return result


def format_report(result: EvalResult, mode: str) -> str:
    return (
        f"Mode: {mode}\n"
        f"Fixtures evaluated: {result.total} (SYNTHETIC, not real profiles)\n"
        f"Identity resolution accuracy: {result.identity_resolution_accuracy:.0%}\n"
        f"Citation coverage: {result.citation_coverage:.0%} "
        f"({result.sourced_or_inference_claims}/{result.total_claims} claims sourced or marked inference)\n"
        f"Average personalisation hooks per brief: {result.avg_hooks:.1f}\n"
        f"Sensitive-content leaks detected: {len(result.sensitive_leaks)}\n"
    )


if __name__ == "__main__":
    res = asyncio.run(run_evaluation())
    print(format_report(res, mode="offline (manual-mode baseline, no live providers)"))
