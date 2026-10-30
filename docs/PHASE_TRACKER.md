# Phase Tracker

| Phase | Backend | Frontend | Tests | GitHub | Status |
|---|---|---|---|---|---|
| 0 | config, auth, /health, /me, migration SQL, worker entrypoint, docker-compose done | Next.js app, Supabase auth client/server/proxy, /login, sidebar+topbar shell, dark mode, typed API client done | 3 auth unit tests pass; tsc/eslint/build clean | all commits pushed | IMPLEMENTED, not VERIFIED (no live Supabase) |
| 1 | input validation, pipeline orchestrator, 7 real stage implementations, research service, POST /research, GET /runs/{id}, SSE, cancel, retry, PDF upload+extraction | New Research form + run detail page (polling, retry/cancel, save-to-prospect) wired to real backend | 100/100 backend tests pass, incl. end-to-end manual-mode pipeline via real HTTP | all commits pushed | IMPLEMENTED in manual mode, VERIFIED via real `curl`/`uvicorn` this session (not TestClient-only) |
| 2 | **AI synthesis now wired end-to-end**: `SynthesiseBriefStage` tries the configured provider (Gemini default, Ollama, or Anthropic), parses structured JSON, retries once on invalid output, then runs the same citation_validator — a fabricated source_id gets dropped even from AI output. Falls back to rule-based synthesis on any failure, always records `_synthesis_metadata.synthesis_method` so the app never lies about which path ran. Bright Data/PDL stubs unchanged | not started | 9 AI-provider tests + 7 synthesizer tests (incl. a test that a fabricated citation is dropped) + 2 full-pipeline tests (rule-based vs AI path) | all commits pushed | IMPLEMENTED, TESTED WITH FIXTURES (fake provider, not a real Gemini/Ollama call) |
| 3 | `LocalExtractionCrawler` (trafilatura + robots.txt + domain restriction) is the default; Firecrawl optional | not started | 12 tests incl. real trafilatura extraction on raw HTML | all commits pushed | IMPLEMENTED (free default), BLOCKED (live crawl against a real domain untested); company persistence/dashboard NOT_STARTED |
| 4 | `DuckDuckGoProvider` (free, keyless) is the default; SearXNG optional; Tavily/Exa/Brave optional. **Identity disambiguation implemented**: name+company intake searches for candidate LinkedIn profiles; 0-1 matches proceed automatically, 2+ pause the run (`needs_identity_selection`) until `POST /runs/{id}/select-identity` is called. `docs/brief-schema.json` now generated directly from the Pydantic model (can't drift) | not started | 10 search tests + 5 identity-resolution tests + 5 identity-disambiguation HTTP tests + 4 schema tests | all commits pushed | IMPLEMENTED, **VERIFIED live** for DuckDuckGo; identity disambiguation TESTED WITH FIXTURES (fake search provider) |
| 5 | ProspectBrief schema, citation validator, rule-based + AI synthesis, JSON/Markdown/PDF export via ReportLab, canonical `docs/brief-schema.json` | prospect detail page has working Export JSON/MD/PDF buttons | 4 export tests incl. a real ReportLab→pdfplumber round-trip | all commits pushed | IMPLEMENTED; brief versioning still only `version=1` (no history/comparison) — NOT_STARTED |
| 6 | Persistent SQLAlchemy models (Company/Prospect/Brief) + `ProspectRepository` + `POST/GET/DELETE /prospects`; a run is never auto-saved — explicit save only | Prospects list + detail pages wired to real saved data (not placeholders); dashboard/companies still placeholder | 9 repository/API tests incl. real SQLite roundtrips, cascade delete, tenant isolation | all commits pushed | IMPLEMENTED (prospects), NOT_STARTED (company persistence, dashboard stats) |
| 7 | 20-fixture eval framework with real measured results (not invented); rate limiting/retention/Ruff/mypy gating still absent | Playwright E2E absent | 2 eval tests, real numbers in docs/EVALUATION_RESULTS.md | all commits pushed | IMPLEMENTED (eval framework), NOT_STARTED (rate limiting, retention, E2E, deployment) |

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

## What's still NOT_STARTED

Real Gemini/Ollama API calls (only fixture-tested), company persistence/
dashboard/companies pages, brief versioning/history/comparison beyond
`version=1`, Playwright E2E, rate limiting, retention/deletion jobs, cost
tracking dashboards, Ruff/mypy as CI gates, and all deployment. See
`docs/KNOWN_LIMITATIONS.md`.
