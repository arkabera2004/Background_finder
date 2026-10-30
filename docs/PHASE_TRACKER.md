# Phase Tracker

| Phase | Backend | Frontend | Tests | GitHub | Status |
|---|---|---|---|---|---|
| 0 | config, auth, /health, /me, migration SQL, worker entrypoint, docker-compose done | Next.js app, Supabase auth client/server/proxy, /login, sidebar+topbar shell, dark mode, typed API client done | 3 auth unit tests pass; tsc/eslint/build clean | all commits pushed | IMPLEMENTED, not VERIFIED (no live Supabase) |
| 1 | input validation, pipeline orchestrator, 7 real stage implementations, research service, POST /research, GET /runs/{id}, SSE, cancel, retry, PDF upload+extraction | New Research form + run detail page (polling, retry/cancel, save-to-prospect) wired to real backend | 100/100 backend tests pass, incl. end-to-end manual-mode pipeline via real HTTP | all commits pushed | IMPLEMENTED in manual mode, VERIFIED via real `curl`/`uvicorn` this session (not TestClient-only) |
| 2 | Gemini + Ollama + Anthropic AI providers behind a common interface (none wired into synthesis yet — synthesis is still rule-based); Bright Data/PDL stubs unchanged | not started | 9 AI-provider tests incl. live Ollama-unreachable check | all commits pushed | IMPLEMENTED (provider layer), BLOCKED (not yet used by synthesis; paid providers) |
| 3 | `LocalExtractionCrawler` (trafilatura + robots.txt + domain restriction) is now the default; Firecrawl optional | not started | 12 tests incl. real trafilatura extraction on raw HTML | all commits pushed | IMPLEMENTED (free default), BLOCKED (live crawl against a real domain untested) |
| 4 | `DuckDuckGoProvider` (free, keyless) is now the default; SearXNG optional; Tavily/Exa/Brave optional | not started | 10 tests incl. **a real live DuckDuckGo search that returned real results** | all commits pushed | IMPLEMENTED, **VERIFIED live** for DuckDuckGo search specifically |
| 5 | ProspectBrief schema, citation validator, rule-based synthesise_brief, **JSON/Markdown/PDF export via ReportLab** | prospect detail page has working Export JSON/MD/PDF buttons | 4 export tests incl. a real ReportLab→pdfplumber round-trip | all commits pushed | IMPLEMENTED (rule-based synthesis + real exports), BLOCKED (LLM-based richer synthesis — Gemini/Ollama provider exists but isn't called from the pipeline yet) |
| 6 | **Persistent SQLAlchemy models** (Company/Prospect/Brief) + `ProspectRepository` + `POST/GET/DELETE /prospects`; a run is never auto-saved — explicit save only | Prospects list + detail pages wired to real saved data (not placeholders); dashboard/companies still placeholder | 9 repository/API tests incl. real SQLite roundtrips, cascade delete, tenant isolation | all commits pushed | IMPLEMENTED (prospects), NOT_STARTED (companies, dashboard stats) |
| 7 | 20-fixture eval framework with **real measured results** (not invented); rate limiting/retention/Ruff/mypy gating still absent | Playwright E2E absent | 2 eval tests, real numbers in docs/EVALUATION_RESULTS.md | all commits pushed | IMPLEMENTED (eval framework), NOT_STARTED (rate limiting, retention, E2E, deployment) |

## This session's actual free-provider migration

- **Default AI provider is now Gemini** (free tier) via `ai_provider` config; Ollama (local, zero-cost) and Anthropic (optional premium) are peers behind one `AiProvider` interface. **Not yet wired into the synthesis stage** — `SynthesiseBriefStage` is still rule-based, not AI-written. Wiring an AI provider into synthesis is the next real piece of work, not done this session.
- **Default search provider is now DuckDuckGo** (free, keyless) — and this was *live-verified*, not just coded: `test_duckduckgo_search_is_live_and_returns_real_urls` made a real network call and got real results.
- **Default extraction is now local** (trafilatura + robots.txt respect + same-domain + page/timeout limits) — Firecrawl is optional, never required.
- Discovered and fixed a real bug this way: the new free-first defaults made every existing pipeline test hit live network, which hung under rate limiting. Fixed via an autouse test fixture that isolates pipeline tests from live network while keeping the dedicated live-provider tests real.

## Explicit domain decision (Part 5A)

A completed research run is **never** automatically a saved Prospect.
`POST /prospects {run_id}` is the only path that promotes a completed
run's brief into a persisted `Prospect` + `Brief` row — verified by
`test_save_prospect_from_completed_run` and
`test_save_prospect_rejects_incomplete_run`. Deleting a Prospect cascades
to its Briefs (tested); the originating Run is independent and unaffected.

## What's still NOT_STARTED

Identity candidate disambiguation (multiple search-based matches — current
`resolve_identity` trusts the submitted identity directly), company
persistence/dashboard stats/companies pages, Playwright E2E, rate
limiting, retention/deletion jobs, cost tracking dashboards, Ruff/mypy as
CI gates, and all deployment. See `docs/KNOWN_LIMITATIONS.md`.
