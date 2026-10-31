# Deployment

## Status: NOT DEPLOYED

No Vercel, Railway, Render, or Supabase project exists for this app. This
document is a checklist for when deployment is authorized — nothing below
has been purchased, provisioned, or deployed.

## Local Docker parity (partially checked this session)

`docker-compose.yml` defines `redis` + `api` (FastAPI/uvicorn) + `worker`
(ARQ). It requires `backend/.env` to exist (copy from `.env.example`) —
`env_file:` fails hard if the file is missing, which was undocumented
before this session; confirmed via `docker compose config`, which also
confirmed the compose file's structure/env mapping is valid. Attempting
`docker build ./backend` and `docker version` in this session's sandbox
hung indefinitely (even `pgrep dockerd` hung) — this looks like a sandbox
restriction on the Docker socket, not a real build problem, but it means
the actual image build was **not verified** this session. Don't treat
`backend/Dockerfile` as confirmed-working until a real `docker build` has
been run somewhere with Docker socket access.

## `.env.example` is now complete

Previously missing `AI_PROVIDER`, `GEMINI_API_KEY`/`GEMINI_MODEL`,
`OLLAMA_BASE_URL`/`OLLAMA_MODEL`, `SEARCH_PROVIDER`, `SEARXNG_BASE_URL`,
`BRAVE_API_KEY`, `EXTRACTION_PROVIDER`, `JINA_READER_API_KEY`, and
`DATABASE_URL` — all of these are read by `app/core/config.py` but a
fresh clone following only `.env.example` would never have known they
existed. Fixed this session; `.env.example` now documents every setting
`Settings` supports.

## Free-tier deployment checklist (when authorized)

1. **Supabase** (free tier) — create project, run
   `backend/migrations/0001_init.sql`, copy `SUPABASE_URL` /
   `SUPABASE_ANON_KEY` / `SUPABASE_SERVICE_ROLE_KEY` / `SUPABASE_JWT_SECRET`
   into both backend and frontend env. RLS policies in the migration are
   written but **never applied to a live database** — verify after first
   apply, don't assume.
2. **Backend API** — Railway or Fly.io free tier, build from
   `backend/Dockerfile`, set env from `.env.example` (leave
   `GEMINI_API_KEY`/`ANTHROPIC_API_KEY`/etc. blank to stay on the Free
   Basic Plan — see `docs/KNOWN_LIMITATIONS.md`), set `DATABASE_URL` to
   the Supabase Postgres connection string (not the SQLite default).
3. **Worker** — same image as the API, run `arq app.workers.main.WorkerSettings`
   as a second Railway/Fly service pointed at the same `REDIS_URL`.
   **Caveat**: `run_store` is currently process-local memory (see
   `docs/SECURITY.md`), so until Runs are persisted to Postgres, the
   worker's retention cron cannot see the API's runs — don't deploy the
   worker expecting retention to actually delete anything yet.
4. **Redis** — Upstash free tier (serverless, works with Railway/Fly) or
   a Redis free-tier addon on whichever host runs the API.
5. **Frontend** — Vercel free tier, set `NEXT_PUBLIC_SUPABASE_URL`,
   `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_API_URL` (pointing at the
   deployed backend).
6. **CORS** — update `CORS_ORIGINS` on the backend to the real Vercel
   domain before anything else works cross-origin.
7. **CI** — `.github/workflows/ci.yml` already runs on push/PR to `main`;
   no change needed for deployment itself, but confirm it's green before
   promoting.

None of steps 1-6 will be created, purchased, or provisioned without
explicit authorization and real credentials, per the project's own
safety rules.

## Rollback

Not applicable yet — nothing has been deployed.
