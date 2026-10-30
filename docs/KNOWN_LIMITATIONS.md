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
- **Gemini/Ollama/Anthropic AI providers**: code exists and is unit-tested
  (including live Ollama-unreachable detection), but **no AI provider is
  called anywhere in the pipeline yet** — `SynthesiseBriefStage` is still
  rule-based. Wiring Gemini into synthesis is the next real step.

## What's real now vs. what's still missing

All seven pipeline stages run end-to-end in manual mode (pasted-text
intake, zero credentials). Real HTTP endpoints exist for research
(`POST /research`, SSE, cancel/retry) and for prospects
(`POST/GET/DELETE /prospects`, brief export as JSON/MD/PDF). The frontend
calls all of these for real, not against placeholder data.

Still NOT_STARTED: identity candidate disambiguation (multiple matches —
currently trusts user input directly), career insights from unstructured
pasted text (works only when structured `Experience` data exists, which
manual paste doesn't produce), company persistence/dashboard/companies
pages, brief versioning beyond `version=1`, `docs/brief-schema.json`,
AI-written synthesis, Playwright E2E, rate limiting, retention jobs, and
deployment.

## No database has ever been touched

The SQL migration (`backend/migrations/0001_init.sql`) has never run against
a real Postgres/Supabase instance. RLS policies are unverified.

## Frontend auth is unverified end-to-end

Login, the auth-redirect proxy, and `/me` integration pass type-checking,
linting, and a production build with placeholder env vars, but have never
been exercised against a real Supabase project or a running backend.
