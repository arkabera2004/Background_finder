# Phase Tracker

| Phase | Backend | Frontend | Tests | GitHub | Status |
|---|---|---|---|---|---|
| 0 | config, auth, /health, /me, migration SQL, worker entrypoint, docker-compose done | Next.js app, Supabase auth client/server/proxy, /login, sidebar+topbar shell, dark mode, typed API client done | 3 auth unit tests pass; tsc/eslint/build clean | all commits pushed | IMPLEMENTED, not VERIFIED (no live Supabase) |
| 1 | input validation, pipeline orchestrator, 7 real stage implementations, research service, POST /research, GET /runs/{id}, SSE, cancel, retry, PDF upload+extraction | New Research form + run detail page (polling, retry/cancel, save-to-prospect) wired to real backend | 100/100 backend tests pass, incl. end-to-end manual-mode pipeline via real HTTP | all commits pushed | IMPLEMENTED in manual mode, VERIFIED via real `curl`/`uvicorn` this session (not TestClient-only) |
| 2 | **AI synthesis now wired end-to-end**: `SynthesiseBriefStage` tries the configured provider (Gemini default, or Anthropic if explicitly selected), parses structured JSON, retries once on invalid output, then runs the same citation_validator — a fabricated source_id gets dropped even from AI output. Falls back to rule-based synthesis on any failure, always records `_synthesis_metadata.synthesis_method` so the app never lies about which path ran. Bright Data/PDL stubs unchanged. **Correction (2026-11-02 audit): Ollama support was removed from `ai_selector.py` at some point after this row was written — the "Ollama" mention above is historical, not current. See `docs/PROJECT_CURRENT_STATE.md` §3/§7.** | not started | 9 AI-provider tests + 7 synthesizer tests (incl. a test that a fabricated citation is dropped) + 2 full-pipeline tests (rule-based vs AI path) | all commits pushed | IMPLEMENTED, TESTED WITH FIXTURES (fake provider, not a real Gemini call) |
| 3 | `LocalExtractionCrawler` (trafilatura + robots.txt + domain restriction) is the default; Firecrawl optional; **Company persistence**: `CompanyRepository` with get_or_create (domain deduplication), list/get/delete methods, all owner-scoped. `GET/DELETE /companies` API endpoints | Companies list page with delete, company detail page with metadata/research data | 5 repository tests + 5 API tests all pass; cascade delete on prospect.company_id, owner isolation verified | all commits pushed | IMPLEMENTED (free default + company persistence), BLOCKED (live crawl untested) |
| 4 | `DuckDuckGoProvider` (free, keyless) is the default; SearXNG/Tavily optional. **Identity disambiguation implemented**: name+company intake searches for candidate LinkedIn profiles; 0-1 matches proceed automatically, 2+ pause the run (`needs_identity_selection`) until `POST /runs/{id}/select-identity` is called. `docs/brief-schema.json` now generated directly from the Pydantic model (can't drift). **Correction (2026-11-02 audit): `exa`/`brave` are accepted config values but `build_search_provider()` has no branch for either — selecting them silently no-ops to `NullSearchProvider`. Not implemented despite appearing in `.env.example`.** | not started | 10 search tests + 5 identity-resolution tests + 5 identity-disambiguation HTTP tests + 4 schema tests | all commits pushed | IMPLEMENTED, **VERIFIED live** for DuckDuckGo; identity disambiguation TESTED WITH FIXTURES (fake search provider) |
| 5 | ProspectBrief schema, citation validator, rule-based + AI synthesis, JSON/Markdown/PDF export via ReportLab, canonical `docs/brief-schema.json`. **Brief versioning**: `ProspectRepository.add_brief_version()`, `get_brief_version()`, `list_brief_versions()`. `GET /prospects/{id}/briefs` (list all versions), `GET /prospects/{id}/briefs/{version}` (specific version) | prospect detail page has working Export JSON/MD/PDF buttons; Dashboard page shows prospect/company counts; Companies list/detail pages wired to real API | 4 export tests + 6 brief versioning tests (add/get/list) + 4 API versioning tests all pass; owner isolation verified | all commits pushed | IMPLEMENTED |
| 6 | Persistent SQLAlchemy models (Company/Prospect/Brief) + `ProspectRepository` + `POST/GET/DELETE /prospects` + `CompanyRepository` + `GET/DELETE /companies`; a run is never auto-saved — explicit save only | Prospects list + detail pages wired to real data; Dashboard shows prospect/company counts; Companies list + detail pages wired to API | 9 prospect repository/API tests + 5 company repository tests + 5 company API tests + 6 brief versioning tests all pass with real SQLite roundtrips, cascade delete, tenant isolation verified | all commits pushed | IMPLEMENTED (full-stack company persistence, brief versioning, dashboard stats) |
| 7 | 20-fixture eval framework with real measured results; **rate limiting** (30 runs/24h/owner via `app/services/rate_limit.py`, settings-driven, 429 on breach); **90-day Run retention** cron (`app/services/retention.py` + ARQ `run_retention_sweep`, settings-driven) — honest caveat: not yet effective since `run_store` is process-local memory, not shared with the worker process; **Ruff + mypy now run clean** (0 errors) and gate CI | Playwright E2E added (7 scenarios, unauthenticated routing/UI only — see `frontend/e2e/README.md`) | 2 eval tests + 5 rate-limit tests + 5 retention tests + cross-owner isolation tests for companies/prospects/briefs; 158 backend tests total | all commits pushed | IMPLEMENTED (eval framework, rate limiting, retention code, CI gates, E2E); BLOCKED (retention not effective until Runs persist to Postgres; no real deployment) |
| 8 (added by 2026-11-02 audit — this work existed in git history but was never written up here) | Brief schema grew to 17 sections (identity verification, education, per-company profiles, same-name/related-people), each new field citation-validated (`0e96535`…`8170a81`). New unified identity-attribution scorer, `app/services/identity_attribution.py`, replacing an earlier two-bucket model with subject/namesake/unverified buckets (`fb94783`), plus five correctness fixes closing real exploits (self-referential fingerprint bootstrap, cross-item fingerprint augmentation, institution-word/title/location false positives — `65393e0`…`f4c2b89`). CI `tsc` fix (`0ff806c`, see below) | Chronos design system adopted across the shell (`a62d782`); `BriefView` rewritten to render all 17 sections (`547f817`); proper-case status labels / progress percentage UI fix (`962d8ae`) | 1 offline regression fixture pinning the attribution-scorer behavior (`04739df`, "Vineet Shukla audit, page-11 checklist"); backend suite now at **283 passing** (verified 2026-11-02, up from the 158 this table last counted) | all commits pushed, **HEAD verified == origin/main at `0ff806c`** | IMPLEMENTED (attribution scorer, 17-section schema, Chronos UI), TESTED WITH FIXTURES (attribution regression fixture is offline/deterministic, not live data) |
| 9 (added by 2026-11-02 audit) | Authenticated Playwright E2E suite (`bcd6b52`, `1a73523`) runs against the **real** Supabase project and real backend — not mocked. CI job `e2e-auth` is manual-dispatch-only (`8843814`) since it costs real Gemini/Supabase usage | n/a (test-only addition) | 6 tests: login/navigation/prospect-library-save **pass live in CI** (confirmed via `gh run view`); the pipeline-completion test (`new-research.spec.ts`) **fails/times out live in CI** in both dispatch attempts on record | pushed | **PARTIALLY VERIFIED LIVE** — 5/6 authenticated E2E specs pass against real infra; the 6th (actual research pipeline completing) is a **currently open, unresolved failure** — this is the most important single finding of the 2026-11-02 audit and the recommended next task (see `docs/NEW_CHAT_HANDOFF.md` §6) |

## This session: AI synthesis + identity disambiguation + brief schema

- **AI synthesis is now real, not just a provider layer sitting unused.** `app/services/ai_brief_synthesizer.py` builds a structured prompt from actual stage outputs, calls the configured `AiProvider`, retries once on invalid JSON, and — critically — re-runs the existing citation validator on the AI's output. A test proves a model that cites a fabricated source_id gets that claim silently dropped, never surfaced.
- **Identity disambiguation is real**, using the already-live DuckDuckGo provider: `check_identity_ambiguity()` searches for `"{name}" "{company}" site:linkedin.com/in`, and 2+ distinct matches pause the run rather than guessing. Tested for ambiguous/unique/no-match cases, including over real HTTP.
- **`docs/brief-schema.json` is generated, not hand-maintained** — `backend/scripts/generate_brief_schema.py` derives it from `ProspectBrief.model_json_schema()`, and a test fails loudly if the model changes without regenerating it.
- All of the above is TESTED WITH FIXTURES (fake AI provider, fake search provider) — none of it has been run against a real Gemini API key, a real Ollama instance, or live DuckDuckGo identity search. That distinction matters and is preserved honestly below.

## Explicit domain decision (Part 5A, carried over)

A completed research run is **never** automatically a saved Prospect.
`POST /prospects {run_id}` is the only path that promotes one — verified
by tests. Deleting a Prospect cascades to its Briefs; the originating Run
is independent and unaffected.

## This session (continuation): Company persistence + brief versioning + frontend completion

- **Company persistence is now full-stack**: `CompanyRepository` with get_or_create (domain-based deduplication for research flow), list/get/delete all owner-scoped. `GET /companies` and `GET /companies/{id}` API endpoints. 5 repository + 5 API tests pass. Frontend `CompaniesPage` fetches real data, company detail page shows metadata and research data, both with proper error handling.
- **Brief versioning is now real**: `ProspectRepository.add_brief_version()` creates new versions by incrementing max version. `get_brief_version()` returns specific version or latest if none specified. `list_brief_versions()` returns all versions ordered by number. `GET /prospects/{id}/briefs` (list) and `GET /prospects/{id}/briefs/{version}` (specific) endpoints. 6 repository + 4 API tests all pass with owner isolation verified.
- **Frontend completion**: Dashboard page now fetches and displays prospect/company counts from the API (not placeholder). Companies list + detail pages fully wired to real API with delete functionality. All pages have proper loading/error states and user feedback.
- Test suite now at **143 backend tests passing** (was 100); frontend builds cleanly with no TypeScript errors.

## This session (continuation 2): E2E, security hardening, CI gates, free-plan verification, deployment docs

- **Playwright E2E** (`frontend/e2e/`): 7 passing tests against a real `next start` build (placeholder Supabase env) verifying the server-side auth middleware redirects every protected route to `/login`, and the login form renders/validates. Authenticated flows remain backend-fixture-tested only — forging a Supabase session without a real project isn't feasible; documented honestly in `e2e/README.md` rather than built around.
- **Rate limiting**: `POST /research` and `/research/pdf` return 429 past `settings.max_runs_per_user_per_day` (default 30/24h), counted against the existing run store — no duplicate state.
- **Retention**: `purge_expired_runs()` deletes Runs older than `settings.default_retention_days` (default 90), wired as a daily ARQ cron. Honestly documented as not yet effective — the worker and API don't share `run_store` in the current in-memory, single-process setup.
- **Tenant isolation**: added cross-owner 404 HTTP tests for companies and brief versions (prospects already had one), closing the gap between repository-level isolation (already tested) and API-level isolation.
- **CI gates**: `.github/workflows/ci.yml` now runs pytest+ruff+mypy+brief-schema-drift (backend) and tsc+eslint+build+Playwright (frontend) on every push/PR to `main`. Ruff/mypy were pinned in `requirements.txt` but never installed or run before this session — installed both, fixed all 7 real findings (unused imports, invariant dict typing, an untyped kwargs dict), 0 errors now.
- **Free Basic Plan — live-verified**: a real local Ollama instance (`gemma3:latest`) was reachable; ran `OllamaProvider.health_check()`, `.complete()`, and the full `synthesize_with_ai()` path end-to-end — returned a valid `ProspectBrief` with `synthesis_method: "ai"`, `estimated_cost_usd: 0.0`. No `GEMINI_API_KEY` is configured, so Gemini remains fixture-tested only; confirmed via code review that `build_ai_provider()` never auto-selects the paid Anthropic provider.
- **Config correctness fix**: `rate_limit.py`/`retention.py` had their own hardcoded constants instead of reading the `max_runs_per_user_per_day`/`default_retention_days` settings that already existed — fixed. `.env.example` was also missing every AI/search/extraction provider var (`AI_PROVIDER`, `GEMINI_*`, `OLLAMA_*`, `SEARCH_PROVIDER`, etc.) and `DATABASE_URL` — completed.
- **Deployment docs**: `docs/DEPLOYMENT.md` now has a concrete free-tier checklist (Supabase + Railway/Fly + Upstash + Vercel) with each step's real caveats called out; no actual deployment attempted, no account created.
- Test suite now at **158 backend tests passing** (was 143); ruff/mypy both 0 errors; frontend Playwright 7/7 passing.

## This session (continuation 3): Research depth + brief structure rewrite

- **ProspectBrief schema rewrite**: structured career timeline (`CareerEntry`), activity classified into 8 required types (`ActivityItem`), `PersonalizationHook`, `OutreachStrategy`, `ResearchGaps`, and richer typed `Source` entries. `docs/brief-schema.json` regenerated from the Pydantic model at every schema-touching task in this change set (Tasks 1 and 7) and re-confirmed in sync at the end of this session (Task 10) — the drift test (`test_schema_file_matches_current_pydantic_model`) passes.
- **Company domain discovery via search** and **deepened company research**: wired into the pipeline stages; TESTED WITH FIXTURES (fake search/crawler providers) only — no live DuckDuckGo company-discovery call beyond the pre-existing live search test was run this session.
- **Activity classification**: a new classifier sorts raw activity signals into the 8 required `ActivityItem` types; covered by unit tests with fixture data only, no live LinkedIn/crawl data.
- **Synthesis rewritten**: `app/services/ai_brief_synthesizer.py`'s prompt and output schema rewritten for the new `ProspectBrief` shape, plus a matching rule-based fallback synthesizer for the same schema. TESTED WITH FIXTURES (fake AI provider) only — no real Gemini/Ollama/Anthropic call was made against the new schema this session (no `GEMINI_API_KEY` configured in this environment; see `docs/KNOWN_LIMITATIONS.md`).
- **Full pipeline wiring**: career, activity, and profile sources wired into brief synthesis end-to-end through the stage pipeline (fixture-tested, not live).
- **Frontend**: `BriefView` rewritten to render all 12 sections of the new `ProspectBrief` structure.
- **Task 10 full verification pass** (this session): `backend && .venv/bin/python -m pytest -q` → **228 passed, 0 failed**. `ruff check app` → 0 errors. `mypy app main.py --ignore-missing-imports` (CI's exact invocation) → 0 errors; the broader whole-package `mypy app` (no ignore flag) still shows the same **16 pre-existing import-untyped errors** for `jose`/`jsonschema`/`reportlab`/`trafilatura` missing stub packages — confirmed these predate this entire plan (present at base commit `2174d27`) and are out of scope (would require adding new dependencies). Frontend: `npx tsc --noEmit` → 0 errors (the previously-noted single `layout.tsx` `LayoutProps` error did not reproduce in this run — Next.js's generated ambient ad-hoc type was already present from an earlier `.next` build in this worktree); `npm run lint` / `npx eslint src` → 0 errors, 2 pre-existing warnings (`no-location-assign-relative-destination` in `login/page.tsx` and `app-topbar.tsx`, both pre-existing); `npm run build` → succeeds. `npx playwright test` (with CI's placeholder Supabase env vars) → **7 passed, 0 failed**, same unauthenticated-routing-only scope as before — no regression from the `BriefView` rewrite. `docs/brief-schema.json` re-regenerated and diffed clean against the working tree — no drift.
- None of this session's new research-depth or brief-structure code has been run against a real Gemini API key, a real Supabase project, or live DuckDuckGo beyond the pre-existing live search test — all of it remains fixture-tested, consistent with the rest of this file's existing honesty convention.

## 2026-11-02 audit session (handoff prep — no feature work done)

This session did not implement anything; it re-verified the repository's actual state
end-to-end because this file and `docs/KNOWN_LIMITATIONS.md` had fallen significantly behind
real commit history (Phases 8/9 above cover ~36 commits made between this file's previous
update and HEAD, none of which had been written up here). Full evidence trail:
`docs/PROJECT_CURRENT_STATE.md`. Headline findings not previously captured anywhere:

- Backend test count is **283 passing** (re-run this session), not the 228 last recorded.
- GitHub Actions `CI` was **red on every push** from `18b32aa` through the second-to-last
  commit (a `tsc`/Next.js-route-types issue), fixed only by the final commit `0ff806c`
  (confirmed via `gh run list`/`gh run view`, not assumed).
- The manual-dispatch `e2e-auth` job (real Supabase + real Gemini) has run twice; login/
  navigation/prospect-save pass live both times, but the actual research-pipeline-completion
  test fails/times out both times — a genuine, open, real-infrastructure problem, not a
  documentation gap. See `docs/NEW_CHAT_HANDOFF.md` for the recommended next task.
- Ollama support was removed from `ai_selector.py` at some point — no longer real; this
  file's Phase 2 row has been corrected in place.
- `search_provider=exa`/`brave` and `JINA_READER_API_KEY` are configured but have no actual
  implementation — corrected in this file's Phase 4 row.

See `docs/NEW_CHAT_HANDOFF.md` for the starter prompt and exact next task for the chat that
picks this up.

## What's still NOT_STARTED

Real Postgres-backed Run storage (the reason retention isn't effective yet), cost tracking dashboards, audit logging, input sanitization for crawled/uploaded content, CORS lockdown beyond localhost, secret rotation, Exa/Brave search, Jina extraction, and all actual deployment (no Supabase/Railway/Vercel account exists). See `docs/KNOWN_LIMITATIONS.md` and `docs/PROJECT_CURRENT_STATE.md`.

## Chanakya Phase 0 — Gap analysis

See `docs/CHANAKYA_GAP_ANALYSIS.md` (`8b54df4`). Scoped Chanakya (monthly
seven-agent GTM engine) as an additive expansion on top of ProspectLens,
reusing its auth/DB/provider/pipeline/citation-validation/export
primitives rather than rewriting them.

## Chanakya Phase 1 — Domain foundation (run lifecycle + provenance)

New, additive module `app/db/chanakya_models.py` (registers alongside
`app/db/models.py` via `app/db/session.py`), separate from ProspectLens's
single-prospect schema:

- `MonthlyRun` — one row per owner per period (e.g. "2026-11"), `status`
  (`pending`/`running`/`completed`/`failed`/`cancelled`), free-form `config`
  JSON for target counts/limits/provider choices set in later phases.
- `OfferingSnapshot` — Agent 01's versioned, append-only offering/ICP brief;
  editing offerings creates a new version rather than mutating history, so
  a completed run always points at the exact brief it ran against.
- `AgentExecution` — one row per agent per run (seeded automatically for
  all seven `AgentName` values on `create_run`), tracking status, retry
  count, error, and an output summary. `start_agent()` is idempotent: if
  the stage is already `COMPLETED` it returns the existing record instead
  of resetting it, so a resumed run never redoes finished work (this is
  the data-layer half of the Phase 9 "restartable and idempotent" monthly
  run requirement — no queue/scheduler yet, that's Phase 9).
- `Evidence` — generic provenance table (`entity_type`/`entity_id`/
  `source_url`/`confidence`/`excerpt`) every later agent (company scout,
  people finder, resolver, email hunter, profile researcher) can attach
  sourcing to from day one, instead of each agent inventing its own
  evidence table per phase.
- `app/schemas/chanakya.py`: `AgentName`, `RunStatus`, `AgentExecutionStatus`
  enums shared by the models, repository, and every later agent.
- `app/db/chanakya_repository.py`: `ChanakyaRunRepository` — owner-scoped
  `create_run`/`get`/`list_for_owner`, `add_offering_snapshot`,
  `start_agent`/`complete_agent`/`fail_agent`, `add_evidence`,
  `mark_run_status`.
- `migrations/0002_chanakya_phase1.sql`: Postgres/Supabase mirror of the
  above with RLS owner policies, additive to `0001_init.sql`.

No API routes or frontend yet — this phase is the shared foundation
Phases 2-8 (the seven agents) build their tables and stages on top of.

Tests: 7 new tests in `app/tests/test_chanakya_run_lifecycle.py` (seed-on-
create, owner scoping, snapshot versioning/append-only, agent
start/complete/fail lifecycle, start-after-complete idempotency, evidence
provenance, run status transitions). Full backend suite: **290 passed**
(up from 283). `ruff check app` → 0 errors. `mypy app main.py
--ignore-missing-imports` → 0 errors. All of this is local SQLite-backed;
none of it has run against a real Supabase/Postgres instance.

## Chanakya Phase 2 — Catalogue Agent (API)

New router `app/api/routers/chanakya.py` (mounted under `/chanakya`,
included in `main.py`), built directly on Phase 1's
`ChanakyaRunRepository`:

- `POST /chanakya/runs` — create a monthly run (`period` validated as
  `YYYY-MM`, optional `config`); seeds all 7 `AgentExecution` rows
  (reused from Phase 1).
- `GET /chanakya/runs`, `GET /chanakya/runs/{id}` — owner-scoped list/get,
  404 cross-owner (matches the existing companies/prospects convention).
- `POST /chanakya/runs/{id}/offerings` — Agent 01: submit/revise the
  offering + ICP brief (`app/schemas/catalogue.py`: `OfferingInput`,
  `OfferingBriefInput`, non-empty validated). Each call creates a new
  `OfferingSnapshot` **version** rather than overwriting — manual
  review/editing never destroys a prior reproducible input — and marks
  the Catalogue `AgentExecution` complete.
- `GET /chanakya/runs/{id}/offerings` — list all versions, oldest first.

No frontend yet (Phase 10 covers the dashboard). No company-discovery
logic yet — that's Phase 3 (Company Scout), which will read the latest
`OfferingSnapshot` this phase produces.

Tests: 8 new in `app/tests/test_chanakya_api.py` (run creation + seeded
executions, period validation, owner scoping including cross-owner 404,
offering submission completing the Catalogue agent, empty-offerings
rejection, re-submission creating version 2 without touching version 1,
404s on an unknown run). Full backend suite: **298 passed** (up from
290). `ruff check app main.py` → 0 errors. `mypy app main.py
--ignore-missing-imports` → 0 errors. SQLite-only; no live Supabase/API
call made.

## Chanakya Phase 3 — Company Scout (Agent 02)

- `app/services/company_scout.py`: `score_fit()` — crude, honest fit
  score (fraction of an offering's ICP-criteria terms found in a search
  result's title/snippet; `0.0` when nothing matches, never fabricated).
  `discover_candidates()` — one search query per ICP criterion (or a bare
  industry query if none given), deduped by domain via a new shared
  helper. `select_top_companies()` — pure ranking by fit score.
- `app/services/company_discovery.py`: extracted `extract_candidate_domain()`
  from the existing `discover_company_domain()` so both the single-company
  resolver and the new multi-company scout share the same aggregator
  blocklist + SSRF-safety check, instead of duplicating it.
- New ORM model `ScoutedCompany` (`chanakya_scouted_companies`, unique on
  `(run_id, domain)`) with `fit_score`/`selected`/`source_url`. Repository:
  `upsert_scouted_companies()` (dedups by domain — re-running discovery
  updates a candidate's score rather than duplicating it),
  `select_top_companies()` (idempotent — re-selecting with a smaller
  target clears the previous selection rather than adding to it, so target
  count changes don't accumulate stale "selected" rows), `list_scouted_companies()`.
- `POST /chanakya/runs/{id}/company-scout`: reads the run's latest
  `OfferingSnapshot` (409 if none submitted yet), builds the configured
  `SearchProvider` (reusing `build_search_provider`, same as the
  single-prospect pipeline), discovers/scores/dedupes/selects
  (`config.target_company_count`, default 100), records one `Evidence`
  row per selected company, marks Company Scout's `AgentExecution`
  complete (or `failed` with the real error on a provider exception,
  surfaced as a 502, not a silently-passed run).
- `GET /chanakya/runs/{id}/companies?selected_only=` — list results.

Tests: 3 service-level (`test_company_scout.py`: fit scoring, dedup +
aggregator filtering, ranking) + 2 repository-level (upsert dedup,
idempotent selection) + 4 API-level (`test_chanakya_api.py`: 409 without
an offering brief, discover→score→select→Evidence→agent-complete happy
path with a fake search provider, configurable target count, selected-only
filter). Full backend suite: **306 passed** (up from 298). `ruff`/`mypy`
both 0 errors. All fixture-tested (fake `SearchProvider`) — no live
DuckDuckGo/Tavily company-discovery call made this phase.

(Note: `migrations/0002_chanakya_phase1.sql` for `chanakya_scouted_companies`
was written in the Phase 4 commit, not here — caught up together.)

## Chanakya Phase 4 — People Finder (Agent 03)

- `app/services/people_finder.py`: `PRIORITY_ROLES` (CEO/CTO/CIO/CDO/VP
  Engineering/VP Product/COO/Head of AI). `extract_name_from_result_title()`
  parses the common LinkedIn search-result title shape ("Name - Role -
  Company | LinkedIn"), returning `None` rather than guessing when the
  format doesn't match. `score_confidence()` rewards a `linkedin.com/in/`
  URL plus company-name/role mentions in the snippet — still never claims
  identity confirmation. `discover_people_for_company()` queries once per
  priority role and dedupes by normalized name. `select_leaders()` ranks
  by confidence and caps at the configured count.
- **Identity is explicitly never confirmed here**: every candidate's
  `identity_confirmed` is hardcoded `False` at creation — only Agent 04
  (LinkedIn Resolver, Phase 5) is allowed to change that, after real
  disambiguation, per the master prompt's "avoid treating uncertain
  identity matches as confirmed."
- New ORM model `Person` (`chanakya_people`, unique on
  `(run_id, company_id, full_name)`), FK'd to `ScoutedCompany`. Repository:
  `upsert_people()` (dedup by name within a company), `list_people()`
  (optionally filtered by `company_id`).
- `POST /chanakya/runs/{id}/people-finder`: iterates every **selected**
  `ScoutedCompany` for the run (409 if Company Scout hasn't selected any
  yet), discovers/ranks/persists up to `config.people_per_company`
  (default 4) leaders per company, records one `Evidence` row per person,
  marks the People Finder `AgentExecution` complete (or failed/502 on a
  real provider error, same pattern as Company Scout).
- `GET /chanakya/runs/{id}/people?company_id=` — list results.
- `migrations/0002_chanakya_phase1.sql` updated with both
  `chanakya_scouted_companies` (Phase 3, previously missing from the
  migration file) and `chanakya_people` tables + RLS policies.

Tests: 4 service-level (name parsing incl. non-match, confidence scoring,
cross-role dedup, ranking+cap) + 1 repository-level (dedup-by-name
upsert) + 3 API-level (409 before company selection, full
discover→select→persist→Evidence→agent-complete happy path across two
companies with a fake provider, list endpoint). Full backend suite:
**313 passed** (up from 306). `ruff`/`mypy` both 0 errors. Fixture-tested
only — no live search call.

## Code organization: one router file per agent

Before Phase 5, `app/api/routers/chanakya.py` (one file covering 3
agents) was split into `app/api/routers/chanakya/` — a package with one
module per agent (`catalogue.py`, `company_scout.py`, `people_finder.py`,
and now `linkedin_resolver.py`), a `shared.py` for the serializers/
lookups every agent needs, and an `__init__.py` aggregating them under
the same `/chanakya` prefix. No endpoint, behavior, or test changed —
313 tests still pass — only which file each endpoint lives in. Each
later agent phase adds its own file here rather than growing a shared
one; `app/services/` already had this per-agent separation
(`company_scout.py`, `people_finder.py`, ...) from Phase 3 onward.

## Chanakya Phase 5 — LinkedIn Resolver (Agent 04)

- `app/services/linkedin_resolver.py`: `resolve_person_identity()` reuses
  `find_identity_candidates()` (already proven in ProspectLens's
  single-prospect identity disambiguation) rather than reimplementing
  search-based matching. Exactly one candidate → `"confirmed"`; zero →
  `"unresolved"`; two or more → `"ambiguous"`. Only the single-match case
  is allowed to set a `linkedin_url` — the master prompt's "no fabricated
  profile URLs" / "avoid treating uncertain matches as confirmed" rule
  enforced in code, not just in the prompt.
- `Person` gains `resolution_status` (`pending`/`confirmed`/`ambiguous`/
  `unresolved`) and `candidate_profiles` (the raw search hits shown to a
  reviewer — never fabricated, exactly what the search provider
  returned). Repository: `apply_resolution()` (auto path — only
  `"confirmed"` sets `identity_confirmed`), `confirm_person_manually()`
  (human picks a profile, always confirms), `get_person()`.
- `POST /chanakya/runs/{id}/linkedin-resolver`: resolves every `pending`
  person on the run against its company; 409 if People Finder hasn't run
  yet. Records `Evidence` for every auto-confirmed person.
- `GET /chanakya/runs/{id}/people/needs-review` — the manual review
  queue: every `ambiguous`/`unresolved` person with their candidate
  profiles attached, for a human to pick from.
- `POST /chanakya/runs/{id}/people/{person_id}/resolve` — manual
  confirmation (`ManualIdentityConfirmation` schema rejects anything that
  isn't a `linkedin.com/in/` URL), always marks `identity_confirmed`.

Tests: 3 service-level (confirmed/ambiguous/unresolved outcomes) + 3
repository-level (apply_resolution confirmed vs. ambiguous, manual
override) + 5 API-level (`test_linkedin_resolver_api.py`: 409 before
People Finder, single-match auto-confirm end-to-end through the whole
agent chain, ambiguous → manual-review-queue → manual resolve, non-
LinkedIn URL rejected, 404 for an unknown person). Full backend suite:
**324 passed** (up from 313). `ruff`/`mypy` both 0 errors. Fixture-tested
only — no live search/Clay/browser call; the master prompt's Clay and
browser-based waterfall tiers ahead of search are not yet implemented
(documented gap, not claimed as done).

## Chanakya Phase 6 — Email Hunter (Agent 05)

- New provider `app/providers/email_verification_provider.py`, same
  honesty convention as `search_provider.py`: `NullEmailVerificationProvider`
  (default) always returns `"unknown"` — it never claims an address is
  valid without a real check. `NeverBounceProvider` is BLOCKED until
  `NEVERBOUNCE_API_KEY` is set. `EMAIL_VERIFICATION_PROVIDER`/
  `NEVERBOUNCE_API_KEY` added to `.env.example`/`Settings`.
- `app/services/email_hunter.py`: `generate_candidate_emails()` produces
  the 5 common professional patterns (first.last, firstlast, f.last,
  flast, first) from a parsed first+last name — returns `[]` for a name
  that doesn't split into two tokens rather than guessing. `verify_candidates()`
  maps a provider's real response to policy: `valid`→accepted,
  `invalid`→`rejected`, `unknown`→`needs_review` (never silently upgraded
  to valid). `select_best_candidate()` prefers a confirmed valid address,
  otherwise the best `needs_review` one for a human to check, `None` if
  every pattern was rejected.
- New `EmailCandidate` table (`chanakya_email_candidates`, unique on
  `(run_id, person_id, email)`), FK'd to `Person`. Repository:
  `upsert_email_candidates()` (dedup by email), `list_email_candidates()`.
- `POST /chanakya/runs/{id}/email-hunter`: for every `identity_confirmed`
  person, generates+verifies+persists candidates against their company's
  domain; 409 if LinkedIn Resolver hasn't confirmed anyone yet. Records
  `Evidence` for the one best candidate per person (when any clears the
  rejected bar).
- `GET /chanakya/runs/{id}/emails?person_id=` — list results.

Tests: 6 service-level (pattern generation incl. empty for a single-token
name, provider-status→policy mapping incl. unknown→needs_review,
best-candidate selection incl. all-rejected→None) + 1 repository-level
(dedup by email) + 3 API-level (409 before confirmed people, full chain
through Company Scout→People Finder→LinkedIn Resolver→Email Hunter with
no verifier configured so everything lands in `needs_review` — honestly,
not faked as verified — and a per-person filter). Full backend suite:
**334 passed** (up from 324). `ruff`/`mypy` both 0 errors. No live
NeverBounce call made; the website/contact-page discovery tier ahead of
pattern-guessing from the master prompt is not yet implemented
(documented gap).

## Chanakya Phase 7 — Profile Researcher (Agent 06)

- `app/services/profile_researcher.py` is deliberately thin:
  `research_person()` drives the **existing** single-prospect pipeline
  (`app/services/research_service.create_run`/`execute_run` — the same
  `ResolveIdentityStage → ... → SynthesiseBriefStage` chain, citation
  validator included) for a confirmed person's name + LinkedIn URL +
  company, and returns exactly what that pipeline produced: `status`
  and `brief`. No new career/activity/company research logic was
  written — Agent 06's job for a *single* person is what ProspectLens
  already does well; this agent's actual contribution is driving it
  across a whole run's confirmed people and persisting the result there.
- New `ResearchBrief` table (`chanakya_research_briefs`, unique on
  `(run_id, person_id)`) — `status` mirrors the underlying pipeline run's
  status; a non-`"completed"` row's `data` stays `{}` rather than a
  partial or fabricated brief. Repository: `upsert_research_brief()`
  (replaces on re-run, doesn't accumulate), `list_research_briefs()`.
- `POST /chanakya/runs/{id}/profile-researcher`: runs research for every
  `identity_confirmed` person (409 if none yet), records `Evidence` from
  each completed brief's own `sources` list (never invents a source),
  tallies completed vs. failed rather than hard-failing the whole agent
  on one person's pipeline failure (the underlying pipeline already
  contains per-stage failures internally).
- `GET /chanakya/runs/{id}/briefs?person_id=` — list results.

Tests: 1 service-level (pipeline-driving contract, accepting whatever
status the real pipeline returns under test's null/rule-based providers)
+ 1 repository-level (replace-on-rerun dedup) + 3 API-level (409 before
confirmed people, full chain through all four prior agents producing one
brief per confirmed person, person-filtered list). Full backend suite:
**339 passed** (up from 334). `ruff`/`mypy` both 0 errors.

## Chanakya Phase 8 — QA and Sync (Agent 07) — all 7 agents now implemented

- `app/services/qa_sync.py`: `score_confidence()` combines three signals
  already produced by earlier agents (identity confirmation, best email
  verification status, research brief completion) into a 0-3 score and
  a high/medium/low level — never invents a fourth signal. `draft_email()`
  builds a subject/body strictly from the brief's own
  `outreach_strategy`/`personalization_hooks` content, falling back to a
  generic (not fabricated) opening when a brief has neither.
- New `QARecord` table (`chanakya_qa_records`, unique on
  `(run_id, person_id)`), `approval_status` starting `"pending_review"`.
  Repository: `upsert_qa_record()` (replaces scoring/draft on re-run,
  **never resets an existing human approval decision**),
  `list_qa_records()` (optional needs-review filter), `get_qa_record()`,
  `set_qa_approval()`.
- `POST /chanakya/runs/{id}/qa-sync`: scores + drafts every person on the
  run (409 if Profile Researcher hasn't produced a brief yet).
- `GET /chanakya/runs/{id}/qa?needs_review_only=` — review queue.
- `POST /chanakya/runs/{id}/qa/{person_id}/approve`: the human approval
  gate the master prompt requires before any send — and this codebase
  has **no email-sending integration at all** (no Outlook/Graph wiring
  exists yet), so "approved" only ever records a decision; nothing here
  sends anything. That absence is the honest, correct state, not a
  shortcut being hidden.
- `GET /chanakya/runs/{id}/export?format=json|csv`: joins QA + person +
  company into export rows (stdlib `csv`, no new dependency); Excel
  (.xlsx) export is not implemented (CSV covers the same data; the
  remaining gap toward the master prompt's "Export center" Excel
  requirement is documented, not claimed done).

Tests: 5 service-level (score levels incl. high/medium/low, draft with a
real hook vs. the generic fallback) + 2 repository-level (replace-
without-resetting-approval, get+approve) + 3 API-level (409 before
briefs exist, full seven-agent chain → score → draft → approve → JSON
and CSV export, 404 for an unknown person). Full backend suite:
**349 passed** (up from 339). `ruff`/`mypy` both 0 errors.

**All seven agents from the master prompt (Catalogue, Company Scout,
People Finder, LinkedIn Resolver, Email Hunter, Profile Researcher, QA
and Sync) now exist as independently testable stages with their own
service/router/schema files, chained end-to-end and covered by
fixture-based tests from run creation through export.** Remaining work
per the master prompt: Phase 9 (queue-based orchestration/scheduling —
today each agent is called by its own explicit API route; there is no
automatic monthly trigger or Service-Bus-style queue yet), Phase 10
(frontend dashboard — none of this has any UI), Phase 11 (security/
privacy hardening beyond existing auth+tenant isolation), Phase 12
(broader test/eval coverage), Phase 13 (Azure deployment), Phase 14
(final acceptance). None of these are claimed done.

## Chanakya Phase 9 (partial) — Orchestration: sequential, resumable run

- `app/api/routers/chanakya/orchestrator.py`: `POST
  /chanakya/runs/{id}/orchestrate` calls Agents 02-07 (Company Scout
  through QA/Sync) in order by calling each one's existing route
  function directly — no logic duplicated. Agent 01 (Catalogue) is
  deliberately excluded: submitting the offering/ICP brief is a human
  review step per the master prompt's workflow step 2, not something to
  auto-trigger.
- **Resumable without a queue**: before calling each stage, the
  orchestrator checks that stage's `AgentExecution.status` — if already
  `"completed"` it's skipped (`"skipped_already_completed"`) rather than
  redone. This works because every agent's persistence from Phase 1
  onward was already built idempotent (`upsert_*` by a unique key); the
  orchestrator adds the "don't even call it again" layer on top of that.
  On a stage failure (any `HTTPException` the stage's handler raises),
  the orchestrator stops immediately and reports `stopped_at` — calling
  `/orchestrate` again resumes at exactly that stage.
- **Still a gap, not claimed as done**: this is one synchronous HTTP
  endpoint, not Azure Service Bus / Container Apps Jobs / a Redis queue.
  There is no automatic monthly cron trigger, no per-stage worker
  process, and no cross-request retry backoff — those remain open Phase
  9 work toward the master prompt's full orchestration architecture.

Tests: 4 API-level (`test_orchestrator_api.py`: 404 for an unknown run,
stopping at Company Scout when no offering brief was submitted, a full
six-stage run to completion, and idempotent re-run — all
`skipped_already_completed`, no duplicate companies/people created).
Full backend suite: **353 passed** (up from 349). `ruff`/`mypy` both
0 errors.
