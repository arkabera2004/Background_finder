"""Phase 4 — scale/performance test at the master prompt's target size:
100 companies, ~400 leaders (4/company, the default), multiple tenants,
multiple monthly runs. Deterministic fake search provider (no live
calls) so the numbers measured are pipeline/DB overhead, not network
variance — the thing this phase is actually supposed to measure.

Run standalone for the printed report: `pytest app/tests/test_scale_load.py -v -s`
"""

import hashlib
import os
import resource
import sys
import tempfile
import time

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.chanakya_repository import ChanakyaRunRepository
from app.db.session import init_db, make_engine
from app.providers.search_provider import SearchProvider, SearchResult
from main import app

client = TestClient(app)

N_COMPANIES = 100
PEOPLE_PER_COMPANY = 4  # DEFAULT_PEOPLE_PER_COMPANY in people_finder.py -> ~400 leaders total

# A true multi-thread concurrency test needs real concurrent connections.
# SQLite ":memory:" uses one shared connection (StaticPool) across every
# thread, which sqlite3 cannot safely drive from multiple OS threads at
# once ("bad parameter or other API misuse") — not a bug in this app, a
# fundamental SQLite dev-mode limitation. A file-backed SQLite DB avoids
# the single-connection trap (each thread gets its own connection, OS
# file locks serialize writes); TEST_POSTGRES_URL, when set, is used
# instead for a real concurrent-connection-pool test.
PG_URL = os.environ.get("TEST_POSTGRES_URL")

_test_session_factory = None


@pytest.fixture(autouse=True)
def _isolated_db(monkeypatch):
    global _test_session_factory

    if PG_URL:
        engine = make_engine(PG_URL)
        from app.db.models import Base

        Base.metadata.drop_all(engine)
        init_db(bind=engine)
    else:
        tmp_path = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
        engine = make_engine(f"sqlite:///{tmp_path}")
        init_db(bind=engine)
    _test_session_factory = sessionmaker(bind=engine)

    from app.api.routers.chanakya import (
        catalogue,
        company_scout,
        email_hunter,
        linkedin_resolver,
        orchestrator,
        people_finder,
        profile_researcher,
        qa_sync,
        schedules,
    )

    for module in (
        catalogue,
        company_scout,
        people_finder,
        linkedin_resolver,
        email_hunter,
        profile_researcher,
        qa_sync,
        orchestrator,
        schedules,
    ):
        monkeypatch.setattr(module, "get_session", lambda: _test_session_factory())
    monkeypatch.setattr(settings, "supabase_jwt_secret", "test-secret")
    monkeypatch.setattr(settings, "max_chanakya_runs_per_user_per_day", 1000)


def _auth_header(user_id: str) -> dict:
    token = jwt.encode(
        {"sub": user_id, "aud": "authenticated", "exp": time.time() + 300},
        "test-secret",
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def _slug(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:10]


class _ScaleSearchProvider(SearchProvider):
    """One deterministic provider covering all three query shapes the
    pipeline issues: company discovery, people-per-role discovery, and
    LinkedIn identity confirmation (always exactly one match, so every
    person auto-confirms rather than piling into manual review — this
    phase measures throughput, not disambiguation behavior)."""

    name = "scale-fake"

    def __init__(self):
        self.call_count = 0

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        self.call_count += 1
        if query.startswith("companies"):
            return [
                SearchResult(
                    url=f"https://company-{_slug(query, str(i))}.example.com/about",
                    title=f"Company {_slug(query, str(i))} fintech Series B",
                    snippet="fintech Series B accelerator",
                )
                for i in range(max_results)
            ]
        if "site:linkedin.com/in" in query:
            full_name, company = query.split('"')[1], query.split('"')[3]
            return [
                SearchResult(
                    url=f"https://linkedin.com/in/{_slug(full_name, company)}",
                    title=f"{full_name} - {company} | LinkedIn",
                )
            ]
        # people-finder role query: '"{company_name}" {role} linkedin'
        company_name, role = query.split('"')[1], query.split('"')[2].strip().removesuffix(" linkedin")
        first = f"Leader{_slug(company_name, role)[:6]}"
        return [
            SearchResult(
                url=f"https://linkedin.com/in/{_slug(company_name, role)}",
                title=f"{first} Doe - {role} - {company_name} | LinkedIn",
            )
        ]


def _run_full_pipeline(monkeypatch, owner_id: str, period: str) -> dict:
    from app.api.routers.chanakya import company_scout as company_scout_router
    from app.api.routers.chanakya import linkedin_resolver as resolver_router
    from app.api.routers.chanakya import people_finder as people_finder_router

    provider = _ScaleSearchProvider()
    monkeypatch.setattr("app.services.company_discovery._is_safe_host", lambda hostname: True)
    monkeypatch.setattr(company_scout_router, "build_search_provider", lambda *a, **k: provider)
    monkeypatch.setattr(people_finder_router, "build_search_provider", lambda *a, **k: provider)
    monkeypatch.setattr(resolver_router, "build_search_provider", lambda *a, **k: provider)

    headers = _auth_header(owner_id)
    run = client.post("/chanakya/runs", json={"period": period}, headers=headers).json()

    # 10 ICP criteria x max_search_results(30) candidates each, deduped by
    # domain, gives well over 100 unique companies for target_company_count
    # to select the top 100 from.
    offerings = [
        {"name": "GenAI Accelerator", "icp_criteria": [f"criterion-{i}" for i in range(10)]}
    ]
    client.post(
        f"/chanakya/runs/{run['id']}/offerings",
        json={"offerings": offerings, "filters": {"industries": ["fintech"]}},
        headers=headers,
    )

    timings: dict[str, float] = {}
    t0 = time.perf_counter()
    response = client.post(f"/chanakya/runs/{run['id']}/orchestrate", headers=headers)
    timings["full_orchestrate_seconds"] = time.perf_counter() - t0
    assert response.status_code == 200
    body = response.json()
    assert body["stopped_at"] is None, body

    return {"run_id": run["id"], "headers": headers, "provider_calls": provider.call_count, **timings}


@pytest.mark.asyncio
async def test_scale_single_tenant_100_companies_400_leaders(monkeypatch):
    mem_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

    result = _run_full_pipeline(monkeypatch, "scale-tenant", "2026-11")

    mem_after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

    headers = result["headers"]
    companies = client.get(f"/chanakya/runs/{result["run_id"]}/companies?selected_only=true", headers=headers).json()
    people = client.get(f"/chanakya/runs/{result['run_id']}/people", headers=headers).json()
    emails = client.get(f"/chanakya/runs/{result['run_id']}/emails", headers=headers).json()
    qa = client.get(f"/chanakya/runs/{result['run_id']}/qa", headers=headers).json()

    assert len(companies) == N_COMPANIES
    assert len(companies) == len({c["domain"] for c in companies})  # duplicate prevention
    # ~4 leaders/company; every selected company got candidates proposed
    assert N_COMPANIES * 2 <= len(people) <= N_COMPANIES * PEOPLE_PER_COMPANY
    assert all(p["identity_confirmed"] for p in people)  # single-candidate fake always confirms
    assert len(emails) == len(people) * 5  # 5 email patterns per confirmed person
    assert len(qa) == len(people)

    # Idempotency / resume: re-running the full orchestrate is a no-op,
    # not a re-fetch or a duplicate-record generator.
    t0 = time.perf_counter()
    rerun = client.post(f"/chanakya/runs/{result['run_id']}/orchestrate", headers=headers).json()
    rerun_seconds = time.perf_counter() - t0
    assert all(s["status"] == "skipped_already_completed" for s in rerun["stages"])
    assert len(client.get(f"/chanakya/runs/{result['run_id']}/people", headers=headers).json()) == len(people)

    rss_unit_divisor = 1024 if sys.platform == "darwin" else 1  # macOS ru_maxrss is bytes, Linux is KB already
    mem_before_kb = mem_before / rss_unit_divisor
    mem_after_kb = mem_after / rss_unit_divisor
    report = (
        f"\n--- SCALE REPORT (single tenant, {len(companies)} companies, {len(people)} leaders) ---\n"
        f"full orchestrate (cold):   {result['full_orchestrate_seconds']:.2f}s\n"
        f"full orchestrate (rerun):  {rerun_seconds:.4f}s (expected ~instant: all stages skipped)\n"
        f"fake provider calls made:  {result['provider_calls']}\n"
        f"peak process RSS before: {mem_before_kb:.0f} KB, after: {mem_after_kb:.0f} KB "
        f"(delta {mem_after_kb - mem_before_kb:.0f} KB — this is whole-process peak RSS, not an "
        f"isolated measurement of just these records)\n"
    )
    print(report)


@pytest.mark.asyncio
async def test_scale_multiple_tenants_concurrent_runs(monkeypatch):
    """Multiple tenants, multiple monthly runs, driven concurrently —
    proves tenant isolation and DB correctness hold under concurrency,
    not just sequentially."""
    import asyncio

    owners = [f"concurrent-tenant-{i}" for i in range(5)]

    async def _one(owner: str) -> dict:
        return await asyncio.to_thread(_run_full_pipeline, monkeypatch, owner, "2026-11")

    t0 = time.perf_counter()
    results = await asyncio.gather(*(_one(o) for o in owners))
    elapsed = time.perf_counter() - t0

    for owner, result in zip(owners, results, strict=True):
        headers = result["headers"]
        companies = client.get(f"/chanakya/runs/{result["run_id"]}/companies?selected_only=true", headers=headers).json()
        assert len(companies) == N_COMPANIES
        # tenant isolation under concurrency: owner X cannot see owner Y's run
        other = owners[(owners.index(owner) + 1) % len(owners)]
        cross = client.get(f"/chanakya/runs/{result['run_id']}/companies", headers=_auth_header(other))
        assert cross.status_code == 404

    session = _test_session_factory()
    repo = ChanakyaRunRepository(session)
    total_runs = sum(len(repo.list_for_owner(o)) for o in owners)
    session.close()
    assert total_runs == len(owners)  # exactly one run per tenant, no cross-contamination

    print(
        f"\n--- SCALE REPORT (5 tenants concurrent) ---\n"
        f"5 full pipelines (100 companies/~400 leaders each) concurrently: {elapsed:.2f}s\n"
    )


@pytest.mark.asyncio
async def test_scale_failure_retry_does_not_duplicate_records(monkeypatch):
    """Simulates a transient failure mid-pipeline (company scout 502s
    once), then a retry — proves the resumable orchestrator doesn't
    duplicate already-persisted records or re-run completed stages,
    even under the full 100-company load."""
    from app.api.routers.chanakya import company_scout as company_scout_router

    real_discover = company_scout_router.discover_candidates
    call_state = {"n": 0}

    async def _flaky_discover(*args, **kwargs):
        call_state["n"] += 1
        if call_state["n"] == 1:
            raise RuntimeError("simulated transient provider outage")
        return await real_discover(*args, **kwargs)

    monkeypatch.setattr(company_scout_router, "discover_candidates", _flaky_discover)

    from app.api.routers.chanakya import linkedin_resolver as resolver_router
    from app.api.routers.chanakya import people_finder as people_finder_router

    provider = _ScaleSearchProvider()
    monkeypatch.setattr("app.services.company_discovery._is_safe_host", lambda hostname: True)
    monkeypatch.setattr(company_scout_router, "build_search_provider", lambda *a, **k: provider)
    monkeypatch.setattr(people_finder_router, "build_search_provider", lambda *a, **k: provider)
    monkeypatch.setattr(resolver_router, "build_search_provider", lambda *a, **k: provider)

    headers = _auth_header("retry-tenant")
    run = client.post("/chanakya/runs", json={"period": "2026-11"}, headers=headers).json()
    client.post(
        f"/chanakya/runs/{run['id']}/offerings",
        json={
            "offerings": [{"name": "GenAI Accelerator", "icp_criteria": [f"c-{i}" for i in range(10)]}],
            "filters": {},
        },
        headers=headers,
    )

    first_attempt = client.post(f"/chanakya/runs/{run['id']}/orchestrate", headers=headers).json()
    assert first_attempt["stopped_at"] == "company_scout"

    retry = client.post(f"/chanakya/runs/{run['id']}/orchestrate", headers=headers).json()
    assert retry["stopped_at"] is None
    assert call_state["n"] == 2  # failed once, succeeded on retry — not re-tried beyond that

    companies = client.get(f"/chanakya/runs/{run["id"]}/companies?selected_only=true", headers=headers).json()
    assert len(companies) == N_COMPANIES
    assert len(companies) == len({c["id"] for c in companies})  # no duplicates from the retry
