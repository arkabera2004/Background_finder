# API Integration

## Backend endpoints that exist today

- `GET /health` — unauthenticated, returns `{"status": "ok"}`.
- `GET /me` — requires `Authorization: Bearer <supabase-jwt>`, returns
  `{"id", "email"}` from the verified token.

Nothing else exists yet. `POST /research`, `/research/resolve`, `/runs/*`,
`/prospects/*`, `/companies/*`, `/products` are all NOT_STARTED.

## External providers — configuration contract, not live wiring

Every provider reads its key from an env var and is designed to fail
loudly (`ProviderUnavailableError`) rather than fabricate data when
unconfigured:

| Provider | Env var | Status |
|---|---|---|
| Supabase | `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET` | configured, no project exists |
| Anthropic | `ANTHROPIC_API_KEY` | configured, no key exists, no client wrapper written yet |
| Tavily | `TAVILY_API_KEY` | configured, not wired to any code yet |
| Exa | `EXA_API_KEY` | configured, not wired to any code yet |
| Firecrawl | `FIRECRAWL_API_KEY` | configured, not wired to any code yet |
| Bright Data | `BRIGHTDATA_API_KEY` | stub provider exists, raises until configured |
| People Data Labs | `PDL_API_KEY` | stub provider exists, raises until configured |

## Frontend → backend contract

`frontend/src/lib/api.ts` attaches the Supabase session's `access_token` as
a Bearer token to every request against `NEXT_PUBLIC_API_URL`. Currently
only `api.health()` and `api.me()` exist.
