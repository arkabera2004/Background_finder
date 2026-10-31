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
- **Gemini/Ollama/Anthropic AI providers**: `SynthesiseBriefStage` tries
  the configured provider first (Gemini default), retries once on invalid
  JSON, then falls back to rule-based synthesis on any failure. Tested with
  a fake provider only — no real Gemini API key or live Ollama instance has
  been exercised this session.

## What's real now vs. what's still missing

All seven pipeline stages run end-to-end in manual mode (pasted-text
intake, zero credentials). Real HTTP endpoints exist for research
(`POST /research`, SSE, cancel/retry), identity disambiguation
(`needs_identity_selection` + `POST /runs/{id}/select-identity`), prospects
(`POST/GET/DELETE /prospects`, brief export as JSON/MD/PDF, version history
via `GET /prospects/{id}/briefs[/{version}]`), and companies
(`GET /companies[/{id}]`, `DELETE /companies/{id}`). The frontend calls all
of these for real, including the Companies and Dashboard pages (no longer
placeholders).

Still NOT_STARTED: Playwright E2E, rate limiting, retention/deletion jobs,
Ruff/mypy as CI gates, and all deployment.

## No database has ever been touched

The SQL migration (`backend/migrations/0001_init.sql`) has never run against
a real Postgres/Supabase instance. RLS policies are unverified.

## Frontend auth is unverified end-to-end

Login, the auth-redirect proxy, and `/me` integration pass type-checking,
linting, and a production build with placeholder env vars, but have never
been exercised against a real Supabase project or a running backend.
