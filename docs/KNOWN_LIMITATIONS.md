# Known Limitations

This file is the single source of truth for what does NOT work yet. If it
isn't listed here, check docs/PHASE_TRACKER.md before assuming it works.

## No live external integrations

Nothing has run against a real Supabase project, Anthropic API, Tavily/Exa,
Firecrawl, Bright Data, or People Data Labs. No account/credential exists for
any of these. Every provider adapter (Bright Data, PDL, Tavily, Firecrawl)
is written and configuration-gated — it reads its key from settings and
either calls the real API or raises/returns-empty when unconfigured —
but the "calls the real API" branch has never executed, since no key
exists to exercise it. See docs/API_INTEGRATION.md for the exact
IMPLEMENTED/BLOCKED split per provider.

## What's real now vs. what's still missing

All seven pipeline stages are now implemented and run end-to-end in
manual mode (pasted-text intake, no credentials) — see
docs/PHASE_TRACKER.md for exactly what each stage does. Real HTTP
endpoints exist: `POST /research`, `POST /research/pdf`, `GET /runs/{id}`,
`GET /runs/{id}/events` (SSE), `/runs/{id}/cancel`, `/runs/{id}/retry`.
The frontend's New Research form and run detail page call these for real.

Still NOT_STARTED: identity candidate disambiguation (multiple matches —
currently trusts user input directly), career insights from unstructured
pasted text (works only when structured `Experience` data exists, which
manual paste doesn't produce), brief exports (JSON/MD/PDF), brief
versioning, `docs/brief-schema.json`, prospect/company persistence beyond
the in-memory run store, dashboard/prospects/companies real data, the
Anthropic client wrapper (synthesis today is rule-based, not AI-written),
Playwright E2E, the 20-profile eval suite, rate limiting, retention jobs,
and deployment.

## No database has ever been touched

The SQL migration (`backend/migrations/0001_init.sql`) has never run against
a real Postgres/Supabase instance. RLS policies are unverified.

## Frontend auth is unverified end-to-end

Login, the auth-redirect proxy, and `/me` integration pass type-checking,
linting, and a production build with placeholder env vars, but have never
been exercised against a real Supabase project or a running backend.
