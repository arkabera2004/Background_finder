# Phase Tracker

| Phase | Backend | Frontend | Tests | GitHub | Status |
|---|---|---|---|---|---|
| 0 | config, auth, /health, /me, migration SQL, worker entrypoint, docker-compose done | not started | auth unit tests passing (3/3); no live DB/Supabase tests possible (no credentials) | all commits pushed | IN_PROGRESS |
| 1 | not started | not started | - | - | PENDING |
| 2 | not started | not started | - | - | PENDING |
| 3 | not started | not started | - | - | PENDING |
| 4 | not started | not started | - | - | PENDING |
| 5 | not started | not started | - | - | PENDING |
| 6 | not started | not started | - | - | PENDING |
| 7 | not started | not started | - | - | PENDING |

Phase 0 is **not** VERIFIED: migrations have never been applied to a
real database (no Supabase project exists), so "database migrations
apply" and "authenticated /me returns correct user ID against real
auth" acceptance criteria are unproven. Frontend half of Phase 0
(Next.js app, Supabase auth, sidebar shell) has not been started.
