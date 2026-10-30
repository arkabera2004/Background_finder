# Phase Tracker

| Phase | Backend | Frontend | Tests | GitHub | Status |
|---|---|---|---|---|---|
| 0 | config, auth, /health, /me, migration SQL, worker entrypoint, docker-compose done | Next.js 15 app, Supabase auth client/server/middleware, /login, sidebar+topbar shell, dark mode, typed API client, placeholder pages done | backend: auth unit tests 3/3 pass. frontend: tsc clean, eslint clean (2 non-blocking warnings), production build succeeds | all commits pushed | IN_PROGRESS |
| 1 | input schemas (URL/name+company/pasted-text validation), Stage interface, pipeline orchestrator (correct dependency order + real concurrency), ProfileProvider abstraction with working ManualProvider and BrightData/PDL stubs | not started | 24/24 backend unit tests pass, incl. a real timing-based concurrency proof | all commits pushed | IN_PROGRESS |
| 2 | not started | not started | - | - | NOT_STARTED |
| 3 | not started | not started | - | - | NOT_STARTED |
| 4 | not started | not started | - | - | NOT_STARTED |
| 5 | not started | not started | - | - | NOT_STARTED |
| 6 | not started | not started | - | - | NOT_STARTED |
| 7 | not started | not started | - | - | NOT_STARTED |

Phase 0 is **IMPLEMENTED, not VERIFIED**: migrations have never been
applied to a real database (no Supabase project exists), so "database
migrations apply", "authentication works", "unauthenticated users are
redirected to login" (proxy.ts logic is correct but untested against a
live Supabase project), and "authenticated /me returns correct user ID"
acceptance criteria are all implemented but unproven against a real
backend. Frontend build/lint/typecheck are green locally with
placeholder Supabase env vars; nothing has been run against real
auth yet.

Phase 1 is **IMPLEMENTED (partially), not VERIFIED**: the credential-free
parts (input validation, pipeline ordering/concurrency, provider fallback
chain with a real working manual path) are built and unit-tested. The
seven stage *implementations* (resolve_identity, fetch_profile, etc. doing
real work), the `POST /research` and `/runs/*` endpoints, SSE progress,
retry/cancel, and all frontend research-flow pages are NOT_STARTED.

Phases 2-7: NOT_STARTED. This includes company research, activity/web
footprint analysis, brief synthesis + citations + exports, the full
frontend research/brief UI, Playwright E2E, the 20-profile evaluation
suite, and deployment. Treat any claim otherwise as false — see
docs/KNOWN_LIMITATIONS.md.
