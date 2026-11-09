# Chanakya Provider Verification (2026-11-09)

Classification of every configured provider against the minimum viable
chain (company discovery → crawl → people → identity → email → verify →
profile research). "Live-verified" below means a real network call was
made this session and its actual response inspected — not assumed from
code reading.

| Stage | Provider | `.env` key present | Status | Evidence |
|---|---|---|---|---|
| Company/people discovery (search) | DuckDuckGo (`ddgs`) | n/a (keyless) | **Live-verified** | `DuckDuckGoProvider().search("Anthropic Claude API")` → 3 real results in 3.33s (`platform.claude.com/docs/...`, `claude.com/platform/api`, …), run this session |
| Company/people discovery (search) | Tavily | `TAVILY_API_KEY` set | Implemented, not live-verified | Real key present in `.env`; not called this session — Tavily is a metered paid API, calling it spends the user's quota without explicit authorization to do so |
| Company/people discovery (search) | SearXNG | `SEARXNG_BASE_URL` empty | Not implemented (falls back to Null) | `build_search_provider` returns `NullSearchProvider` without a base URL |
| Company/people discovery (search) | Exa / Brave | keys empty | Not implemented | Accepted as config values, no provider branch exists (`search_provider.py`) — confirmed by code, not by call |
| Website crawling/extraction | Local (trafilatura, free/keyless) | n/a | **Live-verified** | `LocalExtractionCrawler().crawl(...)` this session: `stripe.com` → 7/9 pages extracted (28.5s), `ycombinator.com` → 4/9 pages (15.5s). `anthropic.com` → 0/9 pages — confirmed to be that specific site's heavy client-side rendering (trafilatura gets no static text), not a crawler defect; a documented limitation (`docs/KNOWN_LIMITATIONS.md`), reproduced live |
| Website crawling/extraction | Firecrawl | `FIRECRAWL_API_KEY` set | Implemented, not live-verified | Real key present; metered paid API, not called without explicit authorization |
| People discovery (leader search) | reuses the search provider above | — | same status as search provider | — |
| Identity resolution (LinkedIn) | search-based heuristic (`find_identity_candidates`) | reuses search provider | Implemented, fixture-tested only | Depends on whichever search provider is active; not exercised against a real ambiguous-name case this session |
| Identity resolution (LinkedIn) | BrightData LinkedIn Scraper API | `BRIGHTDATA_API_KEY` set | Implemented, not live-verified | Real key present; metered paid API (and actual LinkedIn scraping carries its own ToS/rate-limit exposure), not called without explicit authorization |
| Email discovery | pattern-generation (`generate_candidate_emails`) | n/a | **Implemented, deterministic, no live call needed** | Pure function over name+domain patterns — verified by existing fixture tests, nothing to "go live" against |
| Email verification | NeverBounce | `NEVERBOUNCE_API_KEY` **not set** | Not implemented/configured | Code path exists (`NeverBounceProvider`) but no key in `.env` → falls back to `NullEmailVerificationProvider`; confirmed by `.env` inspection |
| Profile research (people data) | PDL (People Data Labs) | `PDL_API_KEY` **not set** | Not implemented/configured | `PDLProvider` exists but no key — same fallback pattern |
| Profile research (people data) | Manual / reused single-prospect pipeline | n/a | **Implemented**, fixture-tested | `ManualProvider` + `research_person()` reuse covered by existing Chanakya Phase 7 tests |
| AI synthesis | Gemini | `GEMINI_API_KEY` set | Implemented, not live-verified this session | Real key present; this session made no Gemini calls (would consume real quota) |
| AI synthesis | Anthropic | `ANTHROPIC_API_KEY` **not set** | Configured as an option, unusable until a key is supplied | `AI_PROVIDER` in `.env` is set to Gemini; Anthropic path exists in code but has no credential |

## What this resolves vs. what still needs your go-ahead

Live-verified **without spending any paid credit**: DuckDuckGo search,
local trafilatura crawling. Both work today, confirmed against real
HTTP responses from real companies (Anthropic, Stripe, Y Combinator),
not fixtures.

**Not exercised, by design**: Tavily, Firecrawl, BrightData, Gemini all
have real keys sitting in `.env` already, but calling any of them spends
the user's real metered quota. The master prompt's own rule is "never
enable billing or consume paid credits without explicit authorization" —
so this session did not call them. If you want one or more of these
live-verified with real spend, say which ones and roughly how many test
calls, and that happens next.

**Genuinely not implemented** (not just "not tried"): NeverBounce and
PDL have no key configured at all — there is nothing to call.
