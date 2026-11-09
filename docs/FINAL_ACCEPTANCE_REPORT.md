# Chanakya Final Acceptance Report

Scope: the 14-phase master prompt to build Chanakya (a seven-agent
monthly GTM prospecting engine) as an additive expansion on top of the
existing ProspectLens single-prospect research tool in this repository.
This report checks the actual state of the code against the master
prompt's section 13 "Definition of done" and section 11 testing/
reliability requirements — honestly, including what is not done.

## Phase-by-phase status

| Phase | Status | Evidence |
|---|---|---|
| 0 — Repository audit, gap analysis | Done | `docs/CHANAKYA_GAP_ANALYSIS.md` |
| 1 — Domain foundation | Done | `chanakya_models.py`/`chanakya_repository.py`, migration `0002_chanakya_phase1.sql` |
| 2 — Catalogue Agent | Done | `catalogue.py` router, versioned `OfferingSnapshot` |
| 3 — Company Scout | Done | `company_scout.py` service+router, dedup+scoring+selection |
| 4 — People Finder | Done | `people_finder.py` service+router, never auto-confirms identity |
| 5 — LinkedIn Resolver | Done | `linkedin_resolver.py`, auto-confirm on 1 match, manual review queue otherwise |
| 6 — Email Hunter | Done | `email_hunter.py`, pattern generation + honest null verification |
| 7 — Profile Researcher | Done | thin driver reusing the existing single-prospect pipeline |
| 8 — QA and Sync | Done | scoring, drafting, human approval gate, JSON/CSV export |
| 9 — Orchestration and resilience | **Partial** | sequential resumable orchestrator exists; no queue, no Azure Service Bus, no automatic monthly trigger |
| 10 — Frontend completion | **Partial** | one connected run dashboard; no multi-offering editor, no manual-review-queue UI, no cost/audit dashboards |
| 11 — Security and privacy hardening | **Partial** | rate limiting, retention, tenant isolation tests done; no audit log, no prompt-injection re-audit for the batch context, no secret rotation |
| 12 — Testing and evaluation | **Partial** | one full deterministic end-to-end test + per-agent tests; no dedicated eval fixtures, no load/scale testing |
| 13 — Azure deployment readiness | **Partial** | deployment guide + cost estimate + a frontend Dockerfile written; **nothing provisioned, Docker build not daemon-verified** |
| 14 — Final acceptance | This document | — |

## Definition-of-done checklist (master prompt §13)

- [x] All seven agents implemented and connected — yes, chained end-to-end (`test_chanakya_end_to_end.py`).
- [x] Monthly run executes end-to-end with deterministic test data — yes.
- [x] Real external providers are configurable and fail gracefully — yes (`Null*Provider` defaults everywhere; a provider exception fails the specific `AgentExecution`, not the process).
- [x] Company and leader records are deduplicated and evidence-backed — yes (`upsert_scouted_companies`/`upsert_people` dedup, `Evidence` table).
- [ ] Research briefs include validated citations — **partially**: this reuses ProspectLens's existing citation validator, which is real, but it was not independently re-verified against Chanakya's batch usage pattern this session.
- [x] QA confidence scoring and human review work — yes, including the review queue and approve/reject gate.
- [x] Email drafts require approval before sending — yes; and there is **no send integration at all**, so nothing can be sent regardless of approval — the safer state, not a gap being hidden.
- [x] Data persistence, exports, and run history work — yes (Postgres-compatible SQLAlchemy models, JSON/CSV export, `GET /chanakya/runs`).
- [x] Frontend workflows are connected to backend APIs — yes, for the one dashboard page built; **not all workflows have a frontend yet** (see Phase 10 gaps).
- [ ] Security, privacy, retention, and tenant isolation are tested — **mostly**: tenant isolation (18 tests) and retention are tested; broader privacy/PII-handling review was not performed this session.
- [x] CI, backend tests, frontend checks, and E2E tests pass — backend 376/376, frontend tsc/eslint/build all clean; **no new Playwright E2E for the Chanakya pages**.
- [ ] Azure deployment is documented and verified to the extent credentials permit — documented; **no credentials existed, so nothing was verified beyond local `next build`/Dockerfile authoring**.
- [x] No fake data or fake success states are presented as real — every doc in this repo, including this one, calls out exactly what is fixture-tested vs. live-verified.
- [x] All work is committed and pushed — every phase landed as its own atomic commit, pushed to `origin/main` (verify with `git log --oneline` / `git status`).
- [x] Final documentation accurately reports verified status and outstanding blockers — this document.

## Outstanding blockers (in priority order for a next session)

1. ~~**No real queue/scheduler**~~ — **RESOLVED 2026-11-09**, see below. Manual HTTP trigger remains available alongside it.
2. **No Azure resources exist** — Phase 13 is guide-only; actually provisioning requires an Azure subscription and credentials this environment doesn't have.
3. **No live external provider has been exercised** — DuckDuckGo/Tavily/NeverBounce/Clay/a browser LinkedIn lookup are all either free-default or unimplemented; real-world discovery/verification quality is unproven.
4. **Frontend coverage is partial** — multi-offering/ICP editing, the manual LinkedIn review queue, and any cost/audit dashboard have no UI.
5. ~~**No test at the target scale**~~ — **RESOLVED 2026-11-09**, see below.
6. ~~**Database is SQLite**, not the Postgres Flexible Server the architecture calls for~~ — **RESOLVED 2026-11-09**, see below.

None of the above are presented elsewhere in this repo's documentation
as resolved. This report exists so a future session (or reviewer) does
not have to re-derive this list from scratch.

## 2026-11-09 update — PostgreSQL verification (blocker 6 resolved)

Ran the real schema against a local PostgreSQL 14 instance (not Docker —
`brew services` Postgres already running on this machine), using the
`psycopg[binary]` driver newly added to `requirements.txt`.

- `Base.metadata.create_all()` (the same path the app uses in production —
  there is no Alembic, by design) creates all 12 tables cleanly against
  `postgresql+psycopg://…/prospectlens_dev` with zero SQLite-specific
  assumptions found — every Chanakya model already used dialect-portable
  `JSON`/`String`/`DateTime` columns.
- New `backend/app/tests/test_postgres_verification.py` (6 tests, gated by
  `TEST_POSTGRES_URL` env var so the default suite still runs on SQLite
  with zero setup) proves against **real Postgres**, not fixtures: schema
  creation, `owner_id` index presence, cross-tenant isolation (`tenant-a`
  cannot read `tenant-b`'s run), explicit rollback discarding an
  uncommitted write, cascade delete removing child `AgentExecution` rows,
  and 5 concurrent threads each opening their own session and committing
  without conflict. All 6 pass.
- Full backend suite: 378 passed + 6 skipped (the Postgres tests, when
  `TEST_POSTGRES_URL` isn't set) — no regression. `ruff`/`mypy` clean.
- **Still not done**: the ~17 existing test files that hardcode
  `make_engine("sqlite:///:memory:")` were not individually migrated to
  run against Postgres too — that would mean touching every one of those
  files, and the new dedicated verification module proves the same
  Postgres-correctness properties without that churn. `DATABASE_URL` is
  not yet switched in `.env`/`.env.example` to point at Postgres by
  default — the app still defaults to SQLite until a real Postgres
  connection string (Supabase or otherwise) is supplied in that file.
  RLS policies mentioned in `migrations/0002_chanakya_phase1.sql` were
  not exercised — tenant isolation here is verified at the ORM/
  application layer (`owner_id` filtering), not at the database layer.

## 2026-11-09 update — durable monthly scheduler (blocker 1 resolved)

New `ChanakyaSchedule` model + `/chanakya/schedules` CRUD API + a daily
ARQ cron (`run_due_chanakya_schedules`, 04:00, alongside the existing
retention sweep at 03:00 — reuses the ARQ cron infrastructure that was
already wired for retention, not a new queueing system). Not
per-tenant-hardcoded: any number of owners can each register any number
of `(offerings, filters, day_of_month)` schedules.

- **Idempotency / no duplicate runs**: `due_schedules()` only returns a
  schedule whose `last_run_period` doesn't already equal the current
  `YYYY-MM`; `ChanakyaRunRepository.get_by_owner_period()` additionally
  makes `POST /chanakya/runs` itself return 409 on a second run for the
  same owner+period, closing the gap at the API layer too (previously
  only an index, not a uniqueness guarantee). New migration
  `0003_chanakya_phase5_scheduler.sql` adds the matching Postgres unique
  constraint and RLS policy — `chanakya_runs` had no RLS policy at all
  until this migration, a pre-existing gap found while doing this work.
- **Failure isolation**: each due schedule runs in its own try/except;
  one tenant's exception is recorded on `last_run_error`/`last_run_status`
  and the loop continues to the next tenant — proven by
  `test_schedule_failure_is_isolated_from_other_tenants`.
- **Execution history**: `last_run_period`/`last_run_id`/`last_run_status`/
  `last_run_error` on the schedule row, plus the full `MonthlyRun` +
  `AgentExecution` records the run itself always produces — no separate
  history table needed, the existing provenance model already is one.
- **Manual trigger still works** — nothing about this touches
  `POST /chanakya/runs` + `/orchestrate`; schedules are an additional
  unattended path, not a replacement.
- 4 new tests (`test_scheduler.py`): CRUD + tenant isolation, rejection
  validation, a full fake-provider-driven run triggered unattended end
  to end (proves company/people/email/brief/QA records are all real,
  not just a 200), and the second-tick-is-a-no-op idempotency check.
  Full suite: 383 passed, 6 skipped (Postgres-gated), ruff/mypy clean.
- **Still not done**: no real monitoring/alerting integration (would
  need Sentry/Slack/PagerDuty — named, not built, since there's no
  account to wire up); retry/backoff is "try again on tomorrow's cron
  tick," not an in-run exponential backoff — acceptable for a monthly
  cadence, not for a tighter SLA; this ARQ cron runs in the worker
  process, which still needs a real Redis + a running worker deployed
  (Azure Container Apps Job, per `docs/DEPLOYMENT_AZURE.md`) to fire in
  production — verified here by calling the function directly in tests,
  not by running the actual `arq` CLI against a live Redis.

## 2026-11-09 update — scale test at target size (blocker 5 resolved)

`backend/app/tests/test_scale_load.py`: a deterministic fake search
provider (no live calls — isolates pipeline/DB overhead from network
variance) drives the full 7-agent pipeline at the master prompt's target
size: 100 selected companies, ~400 confirmed leaders (the `4/company`
default × 100), 5 tenants running concurrently, each a separate monthly
run.

**Measured, not invented** (run on this machine, both against SQLite
and real Postgres — numbers below are SQLite; see "what this found"):

| Metric | Result |
|---|---|
| Full 7-agent pipeline, cold, 100 companies/400 leaders | ~7-9s |
| Same pipeline, re-run (idempotent skip) | ~0.003-0.006s |
| Fake provider calls for one full run | 1,210 |
| 5 tenants running the full pipeline concurrently | ~34-44s total |
| Peak process RSS delta for one run | ~11-14 MB |

**What this found, not just measured:**
- **A real SQLite dev-mode limitation**, not an app bug: `:memory:`
  SQLite uses one shared connection (`StaticPool`) across every
  thread, and `sqlite3` cannot safely run concurrent `cursor.execute()`
  calls on that one connection from multiple OS threads — it raised
  `sqlite3.InterfaceError: bad parameter or other API misuse` under the
  5-tenant concurrency test. Fixed the *test* (switched to a file-backed
  SQLite DB, which gives each thread its own connection) rather than
  the app, since this is inherent to `:memory:` SQLite, not something
  production Postgres has. Re-ran the same test against a real local
  Postgres 14 instance (`TEST_POSTGRES_URL`) — passes cleanly, 5
  concurrent tenants in ~33s, confirming production (Postgres) handles
  this correctly where dev-mode SQLite cannot.
- **Duplicate prevention confirmed at scale**, not just the 1-2 record
  case: 100 companies deduped by domain, re-running the full orchestrate
  produces zero additional records.
- **Retry/resume confirmed at scale**: a simulated transient failure in
  Company Scout (first call raises, second succeeds) still produces
  exactly 100 companies on retry — not duplicated, not short-circuited.
- **Failure isolation across tenants confirmed at scale** (via the
  Phase 5 scheduler tests, same fake-provider pattern): one tenant's
  pipeline failing does not affect another's.

**Still not done**: this is single-machine, single-process concurrency
(threads/asyncio, not separate worker processes or real network
latency to Tavily/Firecrawl/BrightData); a live run against those real
paid providers at this scale has not been attempted (would consume
real quota — same authorization gate as `docs/PROVIDER_VERIFICATION.md`);
no sustained/soak test (this measures one burst, not hours of
sustained load); memory measurement is whole-process peak RSS, not an
isolated per-run figure.
