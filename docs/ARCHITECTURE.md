# Architecture

## Monorepo

- `backend/` — FastAPI app, ARQ worker, Supabase Postgres via migrations.
- `frontend/` — Next.js 15 App Router (built on Next.js 16.4.3 runtime — see
  deviation note below), Supabase Auth, TanStack Query, shadcn/ui.

## Deviation: Next.js version

Project plan specified Next.js 15. `create-next-app@latest` installed
16.4.3, which was the current stable release at scaffold time. Decision:
keep 16.4.3 rather than pin back to 15 — it is the actively supported
release, the App Router APIs used here are unchanged, and two 16-specific
fixes were required and applied (`src/proxy.ts` replacing `middleware.ts`;
`export const instant = false` on the authenticated layout for Cache
Components). Pinning back would mean fighting the scaffolding tool for no
functional benefit. See `docs/DECISION_LOG.md`.

## Backend request flow

`main.py` → CORS middleware → routers (`app/api/routers/*`) → `Depends(get_current_user)`
(`app/core/auth.py`, verifies Supabase JWT with HS256 + `aud=authenticated`).

## Research pipeline (Phase 1, in progress)

`app/stages/pipeline.py` orchestrates seven stages
(`app/stages/base.py::StageName`) in dependency order:

```
resolve_identity -> fetch_profile -> {analyse_career, research_company,
                                       analyse_activity, web_footprint}
                                   -> synthesise_brief
```

The four middle stages run concurrently via `asyncio.gather` once
`fetch_profile` completes. Stage implementations themselves are not written
yet — only the interface, orchestrator, and tests proving the ordering and
concurrency behave correctly with stub stages.

## Profile providers

`app/providers/profile_provider.py` defines the `ProfileProvider` protocol.
`ManualProvider` is the only working implementation (builds a `Person` from
pasted text, no network calls). `BrightDataProvider` and `PDLProvider` are
stubs that raise `ProviderUnavailableError` until credentials and the
20-profile trial (`docs/PROVIDER_EVALUATION.md`) are available.
`app/providers/selector.py::build_provider_chain` always appends
`ManualProvider` last so the product works with zero paid credentials.

## Database

See `backend/migrations/0001_init.sql` for the schema (prospects,
companies, research_runs, run_steps, sources, briefs, products) and
`docs/DATABASE_SCHEMA.md` would cover it in depth once a real Supabase
project exists to verify RLS against — not yet written since there is
nothing to verify.
