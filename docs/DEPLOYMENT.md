# Deployment

## Status: NOT STARTED

No Vercel, Railway, or Render account/project exists. `docker-compose.yml`
and `backend/Dockerfile` exist for local dev parity only — neither has been
built or run (no Docker invocation attempted this session; dependencies
were installed into a local venv for testing instead).

## What's needed before this section can say anything real

1. A Supabase project (URL + keys) — blocks everything downstream.
2. A Railway or Render account for the API + worker + Redis.
3. A Vercel account/project for the frontend, with
   `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`,
   `NEXT_PUBLIC_API_URL` set to the deployed backend's URL.
4. CORS on the backend (`CORS_ORIGINS`) updated to the real Vercel domain.

None of these will be created, purchased, or provisioned without explicit
authorization and real credentials, per the project's own safety rules.

## Rollback

Not applicable yet — nothing has been deployed.
