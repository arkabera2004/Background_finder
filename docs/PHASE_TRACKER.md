# Phase Tracker

| Phase | Backend | Frontend | Tests | GitHub | Status |
|---|---|---|---|---|---|
| 0 | config, auth, /health, /me, migration SQL, worker entrypoint, docker-compose done | Next.js app, Supabase auth client/server/proxy, /login, sidebar+topbar shell, dark mode, typed API client done | 3 auth unit tests pass; tsc/eslint/build clean | all commits pushed | IMPLEMENTED, not VERIFIED (no live Supabase) |
| 1 | input validation, pipeline orchestrator, provider abstractions (profile/search/crawler, all with honest null/manual fallbacks), 7 real stage implementations, research service, POST /research, GET /runs/{id}, SSE events, cancel, retry, PDF upload+extraction | New Research form (3 intake methods) and run detail page (live polling, retry/cancel, brief display) wired to real backend | 67/67 backend tests pass, incl. a full end-to-end manual-mode pipeline run via real HTTP with auth, ownership isolation, and failure paths; frontend build/lint clean | all commits pushed | IMPLEMENTED in manual mode, not VERIFIED against any live provider |
| 2 | Bright Data / PDL adapters exist as typed stubs (raise cleanly, never fabricate) pending accounts + 20-profile trial | not started | provider contract tests pass (unavailable-without-key behavior) | all commits pushed | IMPLEMENTED (manual provider only), BLOCKED (paid providers) |
| 3 | company crawler abstraction + Firecrawl adapter + honest NullCrawler fallback; research_company stage wired | not started | null-fallback tests pass; Firecrawl path untested (no key) | all commits pushed | IMPLEMENTED (interface + fallback), BLOCKED (live crawl) |
| 4 | activity-analysis stage operates on real Person.posts when present; Tavily search adapter + honest NullSearchProvider fallback; web_footprint stage wired | not started | null-fallback tests pass; Tavily path untested (no key) | all commits pushed | IMPLEMENTED (interface + fallback), BLOCKED (live search) |
| 5 | ProspectBrief schema, citation validator (drops unsourced claims/hooks, never invents sources), rule-based synthesise_brief stage | run detail page renders the brief | 5 citation-validator tests + synthesis covered by pipeline integration test | all commits pushed | IMPLEMENTED (rule-based synthesis only — no Anthropic call), BLOCKED (LLM-based richer synthesis) |
| 5 exports | NOT_STARTED | NOT_STARTED | - | - | NOT_STARTED |
| 6 | prospects/companies CRUD, dashboard stats, settings | dashboard/prospects/companies pages still placeholder empty-states, not wired to real data (no persisted prospect/company records exist yet — only in-memory runs) | - | - | NOT_STARTED |
| 7 | rate limiting, retention/deletion, cost tracking, Anthropic client wrapper, Ruff/mypy gating | Playwright E2E | - | - | NOT_STARTED |

## What "IMPLEMENTED in manual mode" actually means (Phase 1)

A real HTTP request to `POST /research` with pasted text, with no API keys
configured anywhere, runs all seven pipeline stages for real, persists
stage-by-stage status, and returns a brief whose only claims are either
directly user-supplied or backed by a real source URL — enforced by the
citation validator, not by convention. This is proven by
`backend/app/tests/test_research_api.py::test_create_research_completes_via_pasted_text`,
which is a real `TestClient` HTTP call, not a mock.

What's still missing even in manual mode: real identity disambiguation
(multiple candidates), career insights beyond "no structured experience
data" (manual paste doesn't produce structured `Experience` records —
only PDF/provider-sourced profiles would), company research beyond
"no crawler configured", and any AI-written prose (synthesis is
template/rule-based, not Claude-generated).

## Phases 2-4: provider pattern now consistent and real

Every external integration (Bright Data, PDL, Tavily, Firecrawl) follows
the same rule: **unconfigured = honest empty result or a typed exception,
never fabricated data.** This was verified by tests asserting empty
lists/exceptions, not by code comments claiming it.

## Phase 5: exports, versioning — NOT_STARTED

JSON export is trivially the brief's own `.model_dump()` (not yet exposed
via an endpoint). Markdown and PDF export, brief versioning, and
`docs/brief-schema.json` do not exist yet.

## Phases 6-7: NOT_STARTED

No prospect/company persistence beyond the in-memory run store (so no
dashboard stats, prospect library, or company detail pages have real data
to show — wiring them to the current run store would be dishonest, since
runs aren't prospects). No Playwright, no 20-profile eval runner, no
Anthropic client wrapper, no rate limiting/retention jobs, no deployment.
See docs/KNOWN_LIMITATIONS.md for the full, current list.
