# Required APIs and Credentials (2026-11-11)

Derived from inspecting both `backend/.env`/`backend/app/core/config.py`
(Chanakya, this repo) and the reference app's `chanakya/config.py`/
`chanakya/llm.py`/`chanakya/adapters.py`/`linkedin_harness.py`. No secret
values are printed anywhere in this document or were printed during the
audit — only variable names and whether a value is present.

## A. Mandatory integrations (app does not run meaningfully without them)

| Service | Purpose | Env var(s) | Status in this repo |
|---|---|---|---|
| Supabase | Auth (JWT/JWKS verification) + Postgres option | `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET` | Configured (URL/anon/service-role keys present; JWT secret empty — verification goes via JWKS fetch, not a local secret, confirmed working) |
| Database | Persistence | `DATABASE_URL` | SQLite by default; Postgres verified separately this session (`docs/FINAL_ACCEPTANCE_REPORT.md`) |
| Redis | ARQ job queue (retention sweep, Phase 5 scheduler) | `REDIS_URL` | Configured |

## B. Search / discovery providers (Company Scout, People Finder, LinkedIn Resolver)

| Provider | Purpose | Env var | Account | Pricing | Status |
|---|---|---|---|---|---|
| DuckDuckGo (`ddgs` package) | Free keyless web search | none | No | Free | **Active now** — `SEARCH_PROVIDER=duckduckgo` as of this session (changed from `tavily` on your explicit instruction) |
| Tavily | Paid search API | `TAVILY_API_KEY` | Yes | Paid/usage-based | Key present in `.env`, **not selected** — do not switch `SEARCH_PROVIDER` back to `tavily` without your explicit approval; it returned HTTP 432 (rate-limit/quota) during this session's testing before the switch |
| SearXNG | Self-hosted meta-search, free | `SEARXNG_BASE_URL` | No (self-hosted) | Free | Not configured |
| Exa / Brave | Accepted as config values | — | — | — | **Not implemented in code** — selecting either silently no-ops to the null provider; do not assume they work |

## C. Crawling / extraction

| Provider | Purpose | Env var | Status |
|---|---|---|---|
| Local extraction (trafilatura) | Free company-page crawling | none | Active default |
| Firecrawl | Paid crawling API | `FIRECRAWL_API_KEY` | Key present, not called this session without authorization |

## D. AI / LLM

| Provider | Purpose | Env var | Status |
|---|---|---|---|
| Gemini | Brief synthesis, email drafting | `GEMINI_API_KEY`, `GEMINI_MODEL` | Configured (`gemini-3.8-flash`), not called live this session (same no-spend-without-approval policy) |
| Anthropic | Alternate AI provider | `ANTHROPIC_API_KEY` | Not configured (empty) |

## E. LinkedIn-specific access — read this before enabling anything here

**There is no officially available, self-serve LinkedIn API for the
company/people-discovery and profile-enrichment use case Chanakya needs.**
LinkedIn's developer platform (`https://learn.microsoft.com/en-us/linkedin/`)
exposes only: Sign In with LinkedIn (OAuth login for your own users),
Share/Post APIs (publishing on behalf of a consenting member), and
Marketing/Talent/Sales Navigator APIs that require a negotiated Partner
Program agreement LinkedIn grants to select companies, not available by
simply creating a developer app. None of these grant bulk profile search
or scraping rights.

Practical, compliant options, in priority order:

1. **Keep the current approach** — DuckDuckGo `site:linkedin.com/in`
   search plus mandatory human review for every non-exact match (already
   built, already the behavior verified this session). This is public-web
   search of pages LinkedIn itself allows search engines to index, not an
   automated session against LinkedIn's own servers.
2. **User-supplied data** — a CSV/export the user downloads themselves
   from their own LinkedIn account (LinkedIn explicitly permits a member
   exporting their own data) and uploads into Chanakya. No new automation
   needed; could be added as a simple importer if useful later.
3. **Sales Navigator / official Partner API**, only if the business is
   able to negotiate that relationship directly with LinkedIn — this is
   not a credential you can self-provision today; if pursued, the contact
   path is `https://business.linkedin.com/sales-solutions/contact-sales`,
   not a developer-portal signup.

**Explicitly excluded**: `linkedin_harness.py`'s browser-automation
approach (real session login + scripted navigation/scraping). See
`docs/LINKEDIN_HARNESS_REFERENCE_AUDIT.md` §8 for the full reasoning. This
was not run against a real LinkedIn account in this session and will not
be integrated.

## F. Optional (quality/coverage improvements, all require your approval before first real call)

| Service | Purpose | Env var | Registration | Payment required | Free tier |
|---|---|---|---|---|---|
| NeverBounce | Real email verification (vs. the current free MX-check heuristic) | `NEVERBOUNCE_API_KEY` | `https://neverbounce.com` | Yes for volume | Small free tier |
| People Data Labs | Profile/person enrichment | `PDL_API_KEY` | `https://www.peopledatalabs.com` | Yes | Limited free tier |
| BrightData | LinkedIn Scraper API (third-party, not LinkedIn-official) | `BRIGHTDATA_API_KEY` | `https://brightdata.com` | Yes | — |

BrightData's "LinkedIn Scraper API" is a **third-party dataset product**,
not an official LinkedIn integration — its own terms of use govern
whether it's compliant for your use case; this was not independently
verified and should not be represented to anyone as an official LinkedIn
API. A key is present in `.env` but it has not been called this session.

## G. Infrastructure

| Service | Purpose | Status |
|---|---|---|
| Supabase | Auth, optional Postgres | Configured, see A |
| Redis | ARQ queue | Configured |
| Azure (Container Apps, Key Vault, Front Door, etc.) | Production deployment target per `docs/DEPLOYMENT_AZURE.md` | Guide only — **no resource provisioned**, requires your subscription + explicit approval before any spend |
| Docker | Local container builds | Confirmed **unavailable in this automation session** (`docs/FINAL_ACCEPTANCE_REPORT.md`) — GUI app can't launch headless; needs you to run builds locally or in CI |

## H. What you need to do, if anything

Nothing is required right now. Current state already runs end-to-end on
free paths: DuckDuckGo (search) + local trafilatura (crawl) + Gemini
(configured but not yet spent against) + Supabase (auth/DB). If you want:

- **Better email verification** → get a NeverBounce key, paste it into
  `backend/.env` yourself (never into chat), set
  `EMAIL_VERIFICATION_PROVIDER=neverbounce`. Free tier is enough to test.
- **Higher-volume/faster search** → re-enabling Tavily is possible, but
  only with your explicit go-ahead given the 432 errors seen this session
  (check your Tavily dashboard for the actual plan/quota first).
- **Real LinkedIn data beyond search-engine results** → see §E; there is
  no quick credential to hand me here, it's a business decision (Sales
  Navigator relationship) or a user-data-import feature, not a config
  change.

`backend/.env.example` already lists every variable name above with no
values — nothing further to add there from this audit.
