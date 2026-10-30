# Known Limitations

This file is the single source of truth for what does NOT work yet. If it
isn't listed here, check docs/PHASE_TRACKER.md before assuming it works.

## No live external integrations

Nothing has run against a real Supabase project, Anthropic API, Tavily/Exa,
Firecrawl, Bright Data, or People Data Labs. No account/credential exists for
any of these. Everything built so far is either:
- pure logic, unit-tested without network access (URL validation, the
  pipeline orchestrator's ordering/concurrency, the manual profile provider), or
- wired to read credentials from env vars but never exercised live.

## Phases 2-7 are not implemented

Only Phase 0 (foundations) and a slice of Phase 1 (research input schemas,
pipeline orchestrator skeleton, provider abstraction with a working manual
fallback) exist. The seven stage *implementations* themselves
(resolve_identity, fetch_profile, analyse_career, research_company,
analyse_activity, web_footprint, synthesise_brief) are not written — only the
interface and orchestrator that will run them. Company research, activity
analysis, web footprint, brief synthesis, citations, exports (JSON/MD/PDF),
the full frontend research/brief UI, Playwright E2E, the 20-profile eval
suite, and deployment are all NOT_STARTED.

## No database has ever been touched

The SQL migration (`backend/migrations/0001_init.sql`) has never run against
a real Postgres/Supabase instance. RLS policies are unverified.

## Frontend auth is unverified end-to-end

Login, the auth-redirect proxy, and `/me` integration pass type-checking,
linting, and a production build with placeholder env vars, but have never
been exercised against a real Supabase project or a running backend.
