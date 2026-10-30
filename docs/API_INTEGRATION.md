# API Integration

## Backend endpoints that exist today

- `GET /health` — unauthenticated, returns `{"status": "ok"}`.
- `GET /me` — requires `Authorization: Bearer <supabase-jwt>`, returns
  `{"id", "email"}` from the verified token.
- `POST /research` — requires auth; body is `ResearchRequest` (one of
  `linkedin_url`, `full_name`+`company`, or `full_name`+`pasted_text`, plus
  `depth`); runs the full 7-stage pipeline in the background, returns
  `{run_id, status}` immediately (202).
- `POST /research/pdf` — multipart upload (`full_name`, `file`, optional
  `depth`); extracts text via pdfplumber (5MB limit), then same as above.
- `GET /runs/{run_id}` — owner-scoped; current status, per-stage status,
  and the brief once completed.
- `GET /runs/{run_id}/events` — SSE stream, polls the same state every
  300ms until a terminal status. Not push-based (no Redis pub-sub running).
- `POST /runs/{run_id}/cancel` — cooperative cancellation, honored between
  stage boundaries.
- `POST /runs/{run_id}/retry` — re-runs a *failed* run from scratch (409 if
  not failed). Per-stage resume is NOT_STARTED.

NOT_STARTED: `/research/resolve` (identity candidate selection — currently
resolve_identity trusts the submitted identity directly since there's no
search provider to find candidates), `/prospects/*`, `/companies/*`,
`/products`, brief export endpoints.

## External providers — what's actually implemented vs. blocked

| Provider | Env var | Status |
|---|---|---|
| Supabase | `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET` | IMPLEMENTED (JWT verify), BLOCKED (no project — DB untouched) |
| Anthropic | `ANTHROPIC_API_KEY` | NOT_STARTED — no client wrapper written; synthesis is rule-based |
| Tavily | `TAVILY_API_KEY` | IMPLEMENTED (`TavilyProvider` in `app/providers/search_provider.py`), BLOCKED (no key, never called live) |
| Exa | `EXA_API_KEY` | NOT_STARTED |
| Firecrawl | `FIRECRAWL_API_KEY` | IMPLEMENTED (`FirecrawlCrawler` in `app/providers/company_crawler.py`), BLOCKED (no key, never called live) |
| Bright Data | `BRIGHTDATA_API_KEY` | STUB — raises `ProviderUnavailableError`/`NotImplementedError`; real adapter NOT_STARTED pending 20-profile trial |
| People Data Labs | `PDL_API_KEY` | STUB — same as above |

Every "IMPLEMENTED" row above means the real HTTP call code exists and
will execute if a key is supplied — not that it has ever been exercised
against the live API. "Never called live" is the honest, current state.

## Frontend → backend contract

`frontend/src/lib/api.ts` attaches the Supabase session's `access_token` as
a Bearer token to every request against `NEXT_PUBLIC_API_URL`. Implemented:
`health()`, `me()`, `createResearch()`, `getRun()`, `cancelRun()`,
`retryRun()`. The New Research form (`/research/new`) and run detail page
(`/runs/[id]`) call these for real — verified via `npm run build` and
manual code review, not yet via a running backend+frontend pair talking
over a real network connection (that would need both dev servers up,
which wasn't done this session).
