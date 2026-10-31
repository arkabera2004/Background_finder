# Known Limitations

This file is the single source of truth for what does NOT work yet. If it
isn't listed here, check docs/PHASE_TRACKER.md before assuming it works.

## No live Supabase / paid-provider integrations

Nothing has run against a real Supabase project, Anthropic API, Tavily/Exa,
Brave, Firecrawl, Bright Data, or People Data Labs. No account/credential
exists for any of these — they're all optional/premium now, never required.
See docs/API_INTEGRATION.md for the exact IMPLEMENTED/BLOCKED split.

## What IS live-verified (free-first providers)

- **DuckDuckGo search**: a real, live, network call in the test suite
  (`test_duckduckgo_search_is_live_and_returns_real_urls`) returns real
  results. This is the default `search_provider`.
- **Local extraction** (trafilatura): verified against real raw HTML in
  tests; not yet verified against a real live website fetch (no network
  fetch was attempted against a real domain this session, only the
  extraction logic itself on a crafted HTML string).
- **Ollama AI provider — LIVE-VERIFIED this session.** A real local Ollama
  instance was reachable at `http://localhost:11434` with `gemma3:latest`
  pulled (not the configured default `llama3.2`, which isn't pulled on
  this machine). Ran `OllamaProvider.health_check()` (true),
  `OllamaProvider.complete()` (returned a real completion), and the full
  `synthesize_with_ai()` path with a real person/source payload — it
  returned a valid `ProspectBrief` with `synthesis_method: "ai"`,
  `provider: "ollama"`, `estimated_cost_usd: 0.0`. This was a manual
  verification, not an automated test (CI has no Ollama instance), so it
  is not re-checked on every run — treat it as a point-in-time confirmation
  that the code path works, not a standing guarantee.
- **Gemini/Anthropic AI providers**: code exists and is unit-tested with a
  fake provider, but no `GEMINI_API_KEY` is configured in this environment,
  so no live Gemini call has been made. `ai_provider` defaults to
  `"gemini"` and `build_ai_provider()` never auto-selects `"anthropic"` —
  confirmed by reading `app/providers/ai_selector.py`.

## What's real now vs. what's still missing

All seven pipeline stages run end-to-end in manual mode (pasted-text
intake, zero credentials). Real HTTP endpoints exist for research
(`POST /research`, SSE, cancel/retry), identity disambiguation
(`needs_identity_selection` + `POST /runs/{id}/select-identity`), prospects
(`POST/GET/DELETE /prospects`, brief export as JSON/MD/PDF, version history
via `GET /prospects/{id}/briefs[/{version}]`), and companies
(`GET /companies[/{id}]`, `DELETE /companies/{id}`). The frontend calls all
of these for real, including the Companies and Dashboard pages (no longer
placeholders). Rate limiting (30 runs/24h/owner), a 90-day Run retention
cron job (not yet effective — see `docs/SECURITY.md`), a GitHub Actions CI
gate (pytest+ruff+mypy+schema-drift+frontend tsc/eslint/build/Playwright),
and a Playwright E2E suite (unauthenticated routing/UI only) all now exist.

Still NOT_STARTED: real Postgres-backed Run storage (currently
process-local memory, which is why the retention cron isn't effective
yet), audit logging, input sanitization for crawled/uploaded content, CORS
lockdown beyond localhost, and all deployment.

## No database has ever been touched

The SQL migration (`backend/migrations/0001_init.sql`) has never run against
a real Postgres/Supabase instance. RLS policies are unverified.

## Frontend auth is unverified end-to-end

Login, the auth-redirect proxy, and `/me` integration pass type-checking,
linting, and a production build with placeholder env vars, but have never
been exercised against a real Supabase project or a running backend.

## Research-depth and brief-structure rewrite (research-depth-and-brief-structure plan) — fixture-tested only

The structured career timeline, 8-type activity classification, company
domain discovery via search, deepened company research, the rewritten
Gemini synthesis prompt/schema and matching rule-based fallback, and the
full 12-section `BriefView` frontend re-render are all TESTED WITH
FIXTURES (fake AI provider, fake search/crawler providers) only. None of
it has been run against a real `GEMINI_API_KEY`, a real Supabase project,
or live DuckDuckGo beyond the pre-existing `test_duckduckgo_search_is_live_and_returns_real_urls`
test — same caveat as the rest of this file. Do not read passing fixture
tests for this work as proof it behaves correctly against a real Gemini
response or real crawled company data.

## Two pre-existing, out-of-scope infra gaps (confirmed still present, not newly introduced)

- **16 mypy stub-package errors**: `mypy app` (whole-package, no
  `--ignore-missing-imports`) reports 16 `import-untyped` errors, all for
  missing type stubs for `jose`, `jsonschema`, `reportlab`, and
  `trafilatura`. These predate the research-depth-and-brief-structure plan
  (present at base commit `2174d27`, before any task in it landed) and
  are out of scope for it — fixing them would mean adding new
  dependencies (`types-python-jose`, `types-jsonschema`, etc.), which is a
  separate decision. CI's actual gate, `mypy app main.py
  --ignore-missing-imports`, passes with 0 errors.
- **1 pre-existing frontend tsc error** on `src/app/layout.tsx` (`Cannot
  find name 'LayoutProps'`) was noted as pre-existing in earlier sessions
  of this plan. It did not reproduce in this session's `npx tsc --noEmit`
  run (0 errors) — Next.js's generated ambient route-prop type was already
  present in this worktree's `.next` build output from an earlier `next
  build`. This is a known quirk of Next.js's typed-routes codegen (the
  type only exists after a build has run at least once), not a fix made
  to the app; it is not tracked as resolved by this plan.
