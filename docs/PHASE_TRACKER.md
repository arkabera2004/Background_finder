# Phase Tracker

| Phase | Backend | Frontend | Tests | GitHub | Status |
|---|---|---|---|---|---|
| 0 | config, auth, /health, /me, migration SQL, worker entrypoint, docker-compose done | Next.js 15 app, Supabase auth client/server/middleware, /login, sidebar+topbar shell, dark mode, typed API client, placeholder pages done | backend: auth unit tests 3/3 pass. frontend: tsc clean, eslint clean (2 non-blocking warnings), production build succeeds | all commits pushed | IN_PROGRESS |
| 1 | not started | not started | - | - | PENDING |
| 2 | not started | not started | - | - | PENDING |
| 3 | not started | not started | - | - | PENDING |
| 4 | not started | not started | - | - | PENDING |
| 5 | not started | not started | - | - | PENDING |
| 6 | not started | not started | - | - | PENDING |
| 7 | not started | not started | - | - | PENDING |

Phase 0 is **not** VERIFIED: migrations have never been applied to a
real database (no Supabase project exists), so "database migrations
apply", "authentication works", "unauthenticated users are redirected
to login" (proxy.ts logic is correct but untested against a live
Supabase project), and "authenticated /me returns correct user ID"
acceptance criteria are all implemented but unproven against a real
backend. Frontend build/lint/typecheck are green locally with
placeholder Supabase env vars; nothing has been run against real
auth yet.
