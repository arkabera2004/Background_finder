# ProspectLens — Current State (Evidence-Based Audit)

**Audit date:** 2026-11-02. Every claim below was verified against the actual repository
and, where noted, GitHub Actions/CLI during this audit — not copied from
`docs/PHASE_TRACKER.md`'s prose, which this audit found to be significantly out of date
(see §13). Do not treat anything in this file as current beyond the commit named in §12 —
re-verify before trusting it in a future session.

## 1. Product purpose and scope

Turns a LinkedIn URL, name+company, pasted profile text, or LinkedIn PDF export into a
sourced Prospect Brief (career timeline, company context, public activity, personalization
hooks, outreach strategy, research gaps, sources). No email generation, no CRM integration,
no bulk research, no Chrome extension, no LinkedIn scraping (v1 exclusions, confirmed still
true by code inspection — see §8).

## 2. Architecture and repository structure

Monorepo: `backend/` (FastAPI) + `frontend/` (Next.js 15 App Router), one GitHub repo. No
separate `prospectlens-backend`/`prospectlens-frontend` repos exist (deliberate decision,
`docs/DECISION_LOG.md`).

```
backend/app/
  api/routers/        health, me, research, companies, prospects (19 route handlers total)
  core/               config (Pydantic Settings), auth (Supabase JWT)
  db/                 memory_store.py (in-process Run storage), company_repository.py,
                      prospect_repository.py, models.py (SQLAlchemy), session.py
  providers/          ai_provider.py, gemini_provider.py, anthropic_provider.py,
                      ai_selector.py, search_provider.py, company_crawler.py,
                      profile_provider.py, bright_data_provider.py, pdl_provider.py, selector.py
  services/           research_service.py, ai_brief_synthesizer.py, identity_attribution.py,
                      rate_limit.py, retention.py, citation_validator.py, activity_classifier.py,
                      career_extractor.py, identity_disambiguation.py, and more
  schemas/            brief.py (ProspectBrief + sub-models), research.py
  workers/            ARQ worker entrypoint (retention cron)
  tests/              92 test source files worth of coverage, 283 tests
  migrations/         0001_init.sql (Supabase Postgres schema + RLS, never applied live)
frontend/src/
  app/(app)/          dashboard, prospects[/id], companies[/id], research/new, runs/[id], settings
  app/login/          Supabase email+Google sign-in
  components/         brief-view.tsx, app-sidebar.tsx, app-topbar.tsx, logo.tsx, ui/ (shadcn)
  lib/supabase/       client.ts, server.ts, middleware.ts (route-protection proxy)
  e2e/                two Playwright suites — unauthenticated (no prereqs) and authenticated
                      (real Supabase + real backend, gitignored session state)
```

## 3. Tech stack (verified from actual dependency/config files, not assumed)

- **Backend**: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy (models exist; default
  `DATABASE_URL=sqlite:///./prospectlens.db`, Postgres swap is config-only), Redis + ARQ
  (worker entrypoint exists; retention cron wired but not effective yet — §8), ReportLab
  (PDF export), trafilatura (free extraction), `ddgs` (DuckDuckGo search).
- **AI providers — actually implemented**: Gemini (`gemini_provider.py`, default) and
  Anthropic (`anthropic_provider.py`, optional, never auto-selected). **Ollama support was
  explicitly removed** — `app/providers/ai_selector.py`'s own docstring states this. Any
  older document or memory claiming a live Ollama verification describes code that no
  longer exists.
- **Search providers — actually implemented**: DuckDuckGo (default, free, keyless), SearXNG
  (optional, needs a base URL), Tavily (optional, needs a key). **`exa` and `brave` are
  listed as acceptable string values in `Settings.search_provider`'s type comment but have
  no corresponding branch in `build_search_provider()`** — selecting either silently falls
  through to `NullSearchProvider` (a no-op). Do not treat EXA_API_KEY/BRAVE_API_KEY as wired
  up; they are not.
- **Extraction providers — actually implemented**: local (trafilatura, default, free) and
  Firecrawl (optional, needs a key). **`JINA_READER_API_KEY` exists in `Settings` and
  `.env.example` but is read nowhere in the codebase** — dead config, not a working
  integration.
- **Profile providers**: `ManualProvider` (paste text/PDF — the only one with a non-stub
  implementation used today), `BrightDataProvider`/`PDLProvider` (classes exist, real HTTP
  calls, but nothing in this audit exercised them with live keys).
- **Frontend**: Next.js 15 (16.4.3 installed) App Router, TypeScript, Tailwind, shadcn/ui on
  Radix primitives, TanStack Query, "Chronos" design system (tokens/brand mark adopted
  2026-11-01, commit `a62d782`).

## 4. Completed functionality, by phase (re-verified, see §9 for exact commands)

| Phase | What exists (code-verified) |
|---|---|
| 0 | Config, Supabase JWT auth, `/health`, `/me`, migration SQL (unapplied), ARQ worker entrypoint, docker-compose. Frontend: Next.js scaffold, Supabase auth client/proxy, `/login`, sidebar+topbar shell. |
| 1 | Input validation (URL/name+company/paste/PDF), 7-stage pipeline orchestrator, `POST /research`, `GET /runs/{id}`, SSE progress, cancel, retry. Frontend: New Research form, run detail page with polling/retry/cancel/save. |
| 2 | AI synthesis wired end-to-end: tries Gemini (default) or Anthropic (if explicitly selected), parses structured JSON, retries once, re-runs the citation validator on AI output (a fabricated `source_id` is dropped even from the model's own output), falls back to rule-based synthesis on failure, records `synthesis_method`. |
| 3 | `LocalExtractionCrawler` (trafilatura, free, default) + optional `FirecrawlCrawler`. Company persistence: `CompanyRepository` (get-or-create by domain, list/get/delete, owner-scoped). `GET/DELETE /companies`. |
| 4 | DuckDuckGo search (default) wired into identity disambiguation: 0–1 LinkedIn-profile search matches proceed automatically; 2+ pause the run (`needs_identity_selection`) until `POST /runs/{id}/select-identity`. `docs/brief-schema.json` generated from the Pydantic model (drift-tested, confirmed not stale as of this audit — §9). |
| 5 | `ProspectBrief` schema, citation validator, rule-based + AI synthesis, JSON/Markdown/PDF export. Brief versioning: `add_brief_version`/`get_brief_version`/`list_brief_versions`, `GET /prospects/{id}/briefs[/{version}]`. |
| 6 | SQLAlchemy `Company`/`Prospect`/`Brief` models, `ProspectRepository`, `POST/GET/DELETE /prospects`. A completed run is never auto-saved — `POST /prospects {run_id}` is the only promotion path (tested). |
| 7 | 20-fixture eval framework, rate limiting (30 runs/24h/owner, 429 on breach), 90-day retention sweep (code correct, not yet effective — §8), ruff+mypy gating CI, unauthenticated Playwright E2E. |
| **8 (undocumented in PHASE_TRACKER before this audit)** | **Chronos design system** adopted across the whole frontend shell (`a62d782`). **Deep-research brief rewrite**: schema grew to 17 sections (identity verification, education, per-company profiles, same-name/related-people disambiguation) with full citation validation on every new field (`0e96535`…`8170a81`). **Unified identity-attribution scorer** (`app/services/identity_attribution.py`) replacing an earlier two-bucket model with subject/namesake/unverified buckets, plus five follow-on correctness fixes to that scorer (self-referential fingerprint exploit, cross-item augmentation exploit, institution-word false positives, title/location false positives) — commits `fb94783`…`f4c2b89`. One offline regression fixture (`04739df`) added specifically to pin this behavior. **Authenticated Playwright E2E suite** added against the real Supabase project and real backend (`bcd6b52`, `1a73523`) — see §6 for its actual CI result, which is a current, unresolved failure. **CI fix** (`0ff806c`) for a `next typegen` ordering bug that had been breaking the frontend CI job on essentially every push since `18b32aa` — see §13. |

## 5. Partially completed functionality

- **Research pipeline against real external services**: DuckDuckGo search is live-verified
  (an existing test hits real DuckDuckGo). Gemini/Anthropic AI synthesis, identity
  disambiguation, company research depth, and the full 17-section brief are all
  **fixture-tested only** (fake AI provider, fake search/crawler providers) — no session has
  run the current schema against a real `GEMINI_API_KEY` and confirmed the output.
- **The authenticated, real-pipeline E2E path**: login, dashboard navigation, and
  save-to-prospect-library against the real Supabase project **do pass** in CI
  (verified in this audit — see §6). The one test that actually submits a research run and
  waits for the pipeline to reach "Completed" **times out and fails** against real
  infrastructure, in both of the two CI attempts this audit found. This is a genuine, current
  gap between "the code compiles and unit-tests pass" and "the live pipeline actually
  finishes a run in CI," not a documentation gap.
- **Retention**: code is correct against its own interface but ineffective, because the
  worker process and the API process don't share the in-memory `run_store` yet (unchanged
  limitation, re-confirmed by code inspection this audit).

## 6. Not-started / explicitly out of scope

Real Postgres-backed Run storage (blocks retention), cost-tracking dashboards, audit logging,
input sanitization for crawled/uploaded content, CORS lockdown beyond localhost, secret
rotation, any actual production deployment (no Supabase/Railway/Vercel account exists — see
§10), Exa/Brave search, Jina extraction (both configured-but-dead, see §3), Bright Data/PDL
live verification, LinkedIn scraping/automation (permanently out of scope by product
decision, not a gap).

## 7. Known bugs, risks, technical debt, limitations

1. **CI was red for ~2 days / ~30 commits** (2026-10-31 06:25 through 2026-11-02 14:50),
   fixed only in the latest commit (`0ff806c`). The frontend job's `tsc --noEmit` failed on a
   fresh checkout because Next.js's generated route types don't exist until a build/dev
   server has run once. Every commit in that window was pushed with a genuinely broken CI
   pipeline, even though the local work itself was fine. **Re-verify this is still green** if
   picking up work after new commits — see §9 for the exact command.
2. **Authenticated E2E pipeline-completion test is currently failing against real
   infrastructure** (§5). Root cause not yet diagnosed in this audit — the trace/error-context
   artifacts from the failing CI run (`npx playwright show-trace` output) are the fastest way
   to start.
3. **Three dead/partially-dead config surfaces**: `search_provider=exa`, `search_provider=brave`
   (silently become a no-op search provider), `JINA_READER_API_KEY` (read nowhere). Anyone
   setting these expecting them to work will get silent non-functionality, not an error.
4. **Ollama references in older documentation/memory are stale** — the provider was removed;
   do not re-introduce it without checking why it was removed first (no removal rationale was
   found in `docs/DECISION_LOG.md` — worth asking before assuming it was deliberate scope-cut
   vs. an unintentional regression).
5. `run_store` in-memory-only (±everything downstream of it: retention, rate limiting across
   processes) — unchanged, known, documented limitation.
6. `docs/README.md` and `CLAUDE.md`'s "Current status" pointers are themselves stale in tone
   (README still says "only Phase 0 backend scaffolding exists") — not fixed in this audit
   (out of this audit's requested scope), but worth a follow-up pass.
7. An untracked plan file, `docs/superpowers/plans/2026-10-31-research-depth-and-brief-structure.md`,
   sits in the working tree uncommitted. Its 10 tasks all appear to have been completed (the
   schema/synthesis/frontend work it describes matches what's actually in the code) — it
   looks like a completed plan that was never committed or cleaned up, not in-progress work.
   Decide whether to commit it (as a historical record) or delete it; don't silently keep
   carrying it as clutter.

## 8. API/provider integrations, categorized

| Provider | Category |
|---|---|
| DuckDuckGo search | **Live-verified** (existing test hits real DuckDuckGo over HTTP) |
| Supabase Auth (JWT verification logic) | **Tested with mocks** (forged/invalid signatures) — never tested against a real Supabase-issued token in the backend's own unit tests, but **is** exercised live by the authenticated E2E suite's login step, which does pass in CI |
| Gemini AI synthesis | **Configured, fixture-tested only** — no real `GEMINI_API_KEY` call confirmed in any session's local work; **but** the authenticated E2E suite runs against real infra including real AI, and that path's completion step is the one currently failing (§5) — so "configured but not verified" is the honest state, leaning toward "verified it doesn't reliably complete in time," not "verified it works" |
| Anthropic AI | Planned/configured, never auto-selected, not exercised live |
| SearXNG, Tavily | Configured, not exercised live (no base URL / API key in this environment) |
| Exa, Brave search | **Planned in name only — not implemented** (§3, §7) |
| trafilatura local extraction | **Live-verified** (used by default; the pre-existing crawler tests include real extraction logic, though company-crawl-against-a-real-target-site live run is still flagged BLOCKED in PHASE_TRACKER's phase 3 and not re-verified in this audit) |
| Firecrawl extraction | Configured, optional, not exercised live |
| Jina Reader | **Dead config — not implemented** (§3, §7) |
| Bright Data, PDL profile providers | Implemented as real HTTP-calling classes, never exercised with live keys |
| ManualProvider (paste/PDF) | **Implemented and tested** (the only profile provider used in all pipeline tests) |

## 9. Database and persistence status

- SQLite by default (`DATABASE_URL=sqlite:///./prospectlens.db`), Postgres swap is
  config-only (same SQLAlchemy models, confirmed by reading `app/db/session.py`).
- `Company`/`Prospect`/`Brief` are persisted via SQLAlchemy + repositories, with
  cascade-delete (Prospect → Brief) and owner-scoped cross-tenant isolation — **tested** (9
  prospect + 5 company + 6 brief-versioning repository/API tests, all passing in this audit's
  run — see §10).
- `Run` (a research pipeline execution) is **not** persisted — in-process memory
  (`app/db/memory_store.py`), lost on restart, not shared between the API and worker
  processes. This is the single biggest "not production-ready" fact about the data layer.
- The Supabase migration (`backend/migrations/0001_init.sql`) defines the intended schema and
  RLS policies but has **never been applied to a real database** — no Supabase project
  exists in this environment (confirmed: `backend/.env` exists locally but this audit did not
  inspect or need its values, per the task's "no secret values" instruction; its mere
  presence does not by itself confirm a live, reachable Supabase project — that would require
  an actual network call this audit did not make).

## 10. Authentication, authorization, tenancy, security

Unchanged from `docs/SECURITY.md`, re-confirmed by code reading this audit:

- Supabase JWT (HS256) verification in `app/core/auth.py`, unit-tested against forged tokens.
- RLS policies exist in the migration SQL, scoped to `owner_id = auth.uid()`, never applied
  live.
- Every company/prospect/brief endpoint filters by `owner_id`; cross-owner access returns 404
  (tested).
- Rate limiting: 30 runs/24h/owner, 429 on breach (tested, in-memory, not cross-process).
- No audit logging, no crawled-content sanitization, no CORS lockdown beyond localhost, no
  secret rotation — all explicitly NOT_STARTED (Phase 7+ scope).
- `docs/SECURITY.md` itself is slightly stale (says "Phase 4/5 not started" for
  sensitive-attribute inference; Phase 4/5 are now implemented) — not fixed in this audit
  (out of the four requested files), flagged here for a future pass.

## 11. Frontend workflow status

All pages (`dashboard`, `research/new`, `runs/[id]`, `prospects[/id]`, `companies[/id]`,
`settings`, `login`) exist, build cleanly, and are wired to the real backend API client
(`lib/api.ts`) — none are placeholder/mock data as of this audit (re-confirmed: Dashboard
fetches real counts, Companies/Prospects pages fetch real lists). The Chronos design system
reskin (`a62d782`) and the 17-section `BriefView` rewrite (`547f817`) are the two largest
unreviewed-by-a-human-session frontend changes — both compile and pass the unauthenticated
E2E suite, but have not been manually clicked through by any session with real data, and the
authenticated E2E suite's one content-bearing test (submit → see rendered brief) is the one
currently failing in CI (§5).

## 12. Test results and exact commands run (this audit, 2026-11-02)

```
cd backend && .venv/bin/python -m pytest -q
  → 283 passed, 74 warnings (deprecation warnings only, no failures), 9.23s

cd backend && .venv/bin/ruff check app main.py
  → All checks passed!

cd backend && .venv/bin/mypy app main.py --ignore-missing-imports   # CI's exact invocation
  → Success: no issues found in 92 source files

cd frontend && npx tsc --noEmit
  → exit 0, no output (clean)

cd frontend && npx eslint src
  → 0 errors, 3 warnings (2 pre-existing window.location.href warnings;
    1 NEW, previously undocumented: no-img-element in components/logo.tsx,
    introduced by the Chronos design adoption)

cd frontend && npm run build
  → succeeds, 13 routes generated (static/dynamic/PPR mixed)

cd frontend && npx playwright test --config=playwright.config.ts   # unauthenticated suite
  → 7 passed (33.1s)

cd backend && PYTHONPATH=. .venv/bin/python scripts/generate_brief_schema.py \
  && git diff --exit-code docs/brief-schema.json
  → no drift (schema file matches current Pydantic model)
```

**Not run in this audit** (and why): the authenticated Playwright suite
(`npm run test:e2e:auth`) needs `E2E_EMAIL`/`E2E_PASSWORD` for a real Supabase test account,
which are not available in this local environment. Its actual, current result **was**
obtained — not by running it, but by inspecting real GitHub Actions run history (`gh run
view`), which is equally authoritative and avoids spending real API/AI cost redundantly. See
§13 for the exact finding.

## 13. CI / deployment status — what is and is not actually running

- **GitHub Actions `CI` workflow** (`.github/workflows/ci.yml`): `backend` and `frontend` jobs
  run on every push/PR to `main`. **Confirmed via `gh run list`**: every push-triggered run
  from `18b32aa` (2026-10-31 ~01:28) through the second-to-last commit failed on the
  frontend job's `tsc --noEmit` step (missing Next.js route types on a fresh checkout — a
  known class of issue, not a logic bug). The very latest push (`0ff806c`) fixed this by
  running `npx next typegen` before `tsc` and **is green**.
- **`e2e-auth` job** (manual `workflow_dispatch` only, added `8843814`): runs against the real
  Supabase project and real backend/frontend dev servers with repo secrets `E2E_EMAIL`/
  `E2E_PASSWORD` already configured (confirmed present — their values were not inspected).
  **Confirmed via `gh run view` on the two dispatch attempts that exist**: login (`auth.setup.ts`),
  dashboard/sidebar navigation, and prospect-library save all **pass**. The
  `new-research.spec.ts` test — submit pasted-text research, wait for the pipeline to reach a
  terminal "Completed" state — **fails both times**, timing out after the test's own 260-second
  budget waiting for the "Save to Prospect Library" button to appear. **This is the single
  most important, concrete, currently-unresolved finding of this audit**: the real pipeline,
  against real Gemini + real Supabase, is not finishing within the test's timeout (or is
  failing silently before reaching the UI state the test checks for) in the CI environment.
- **No actual deployment exists anywhere** — no Railway/Render/Fly/Vercel account, confirmed
  by `docs/DECISION_LOG.md` and re-confirmed by the absence of any deployment-specific
  secrets, URLs, or `gh` deployment records found in this audit. `docs/DEPLOYMENT.md`
  describes a planned free-tier checklist, not a completed deployment.

## 14. Environment variables (names only — see each file for which are required vs. optional)

**`backend/.env.example`**: `ENVIRONMENT`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`,
`SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`, `REDIS_URL`, `AI_PROVIDER`,
`GEMINI_API_KEY`, `GEMINI_MODEL`, `ANTHROPIC_API_KEY`, `CLAUDE_MODEL_FAST`,
`CLAUDE_MODEL_SMART`, `SEARCH_PROVIDER`, `SEARXNG_BASE_URL`, `TAVILY_API_KEY`, `EXA_API_KEY`
(dead — §3), `BRAVE_API_KEY` (dead — §3), `EXTRACTION_PROVIDER`, `FIRECRAWL_API_KEY`,
`JINA_READER_API_KEY` (dead — §3), `BRIGHTDATA_API_KEY`, `PDL_API_KEY`,
`MAX_RUNS_PER_USER_PER_DAY`, `MAX_CONCURRENT_RUNS_PER_USER`, `DEFAULT_RETENTION_DAYS`,
`DATABASE_URL`, `CORS_ORIGINS`.

**`frontend/.env.example`**: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`,
`NEXT_PUBLIC_API_URL`.

**CI-only secrets** (GitHub Actions repo secrets, confirmed present, values not inspected):
`E2E_EMAIL`, `E2E_PASSWORD`.

## 15. Git status and latest commit (verified at audit time)

- Branch: `main`. Local HEAD **matches** `origin/main`.
- HEAD: `0ff806cd650d3d31abaf193360f6001bab610fc9` —
  `fix(ci): generate Next.js route types before tsc, fixing a real CI failure` (2026-11-02
  20:22:03 +0530).
- Working tree: **not clean** — one modified-but-uncommitted file (`.gitignore`, adds
  `.worktrees/`) and one untracked file (the plan doc in §7 item 7). Both pre-date this audit;
  neither was created by it.
- Remote: `origin` → `https://github.com/arkabera2004/Background_finder.git` (fetch+push).

## 16. Prioritized remaining work

1. **Diagnose and fix the authenticated E2E pipeline-completion failure** (§5, §13) — this is
   the one concrete, currently-failing, real-infrastructure test blocking confidence in the
   live path. Start with the trace artifact from the failing CI run.
2. **Decide the fate of the three dead config surfaces** (Exa/Brave search, Jina extraction) —
   either implement them or remove them from `.env.example`/settings so they stop looking
   wired-up when they aren't.
3. **Move `Run` storage off in-process memory** (Postgres or Redis-backed) — this is the
   prerequisite for retention actually working and for the worker/API split to be real.
4. **Resolve the two uncommitted working-tree items** (§7 item 7, §15) — commit or discard.
5. **Refresh `README.md`/`CLAUDE.md`'s stale "current status" prose** and `docs/SECURITY.md`'s
   stale Phase 4/5 note (not done in this audit — out of its four-file scope, but a fast
   follow-up).
6. Continue toward an actual deployment (Supabase project, Railway/Fly backend, Vercel
   frontend) once the E2E blocker in item 1 is resolved — deploying before that risks shipping
   a pipeline that doesn't reliably finish.
