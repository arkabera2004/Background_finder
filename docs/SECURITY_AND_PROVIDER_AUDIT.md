# Security and Provider Audit (2026-11-13)

No paid API was called during this audit. No secret value is printed
anywhere in this document.

## 1. Active provider configuration (verified live, this session)

```
search_provider: duckduckgo
extraction_provider: local
ai_provider: gemini
email_verification_provider: null
```

Confirmed via `settings.search_provider`/etc. read directly from the
running backend process (not from `.env` text, which could be stale
relative to what the process actually loaded) and cross-checked against
the live `/chanakya/integrations` endpoint in the browser, which showed
"DuckDuckGo: active" and "Local extraction (trafilatura): active".

## 2. Silent-fallback check — none found

Every provider selector (`build_search_provider`, `build_company_crawler`)
takes the active choice as an explicit argument, always sourced from
`settings.search_provider` / `settings.extraction_provider` at every one
of its 6 call sites (`company_scout.py`, `people_finder.py`,
`linkedin_resolver.py`, `research_service.py` ×3). None of them hardcode
`"tavily"` or `"firecrawl"` anywhere. Selecting an unconfigured paid
provider returns `NullSearchProvider`/`NullCrawler` (an honest empty
result), never a fabricated response and never an automatic escalation
to a different paid provider.

## 3. A third real paid-API code path found — not yet exercised, present by design

`app/providers/selector.py`'s `build_provider_chain()` orders **paid
providers first** when configured: `BrightDataProvider` before
`PDLProvider` before the free `ManualProvider`. `BRIGHTDATA_API_KEY` is
genuinely present in `.env`. This path is **not** part of the 7 Chanakya
agents — it's `app/services/research_service.py`'s `FetchProfileStage`,
used by ProspectLens's original single-prospect `POST /research`
endpoint, for a request that supplies a real LinkedIn URL (not pasted
text).

**This means**: any call to `/research` with a LinkedIn URL and no
pasted profile text will, by this code's own design intent ("paid
providers first"), attempt a real BrightData API call before falling
back to anything else. Unlike Tavily/Firecrawl, there is no equivalent
*free* provider in this chain that does the same job (real LinkedIn
profile fetch) — `ManualProvider` requires the user to paste the
profile text themselves, it doesn't fetch anything. So this isn't a
"redirect to a free alternative" fix; it is a real, intentional paid
capability that is currently reachable by default.

Not exercised this session (no `/research` call was made with a bare
LinkedIn URL and no pasted text), and not changed — this needs **your**
decision: keep BrightData reachable by default (it's the only way this
app does a real live LinkedIn lookup for ProspectLens), or require an
explicit flag before that code path is reachable. `PDL_API_KEY` is
empty, so PDL is correctly inert.

## 4. Secret-exposure checks

| Check | Result |
|---|---|
| `.env` tracked in git, any commit, ever | **No** — `git log --all --diff-filter=A -- '*.env' '.env*'` found zero matches (only `.env.example` files, which contain no values) |
| `backend/.env` gitignored | **Yes** — `.gitignore:5` |
| `frontend/.env.local` gitignored | **Yes** — `frontend/.gitignore:34` |
| Any secret key bundled client-side (`NEXT_PUBLIC_*`) | **No** — only `NEXT_PUBLIC_SUPABASE_ANON_KEY` (Supabase's own anon key, designed to be public, RLS-protected) and `NEXT_PUBLIC_API_URL` (not a secret) are ever referenced with that prefix |
| `settings` object ever logged, printed, or serialized wholesale | **No** matches found in any non-test source file |
| Current backend/session logs contain any API-key-shaped string | **No** matches for `api_key`/provider names in this session's log files |
| `GET /chanakya/integrations` response leaks a secret value | **No** — explicitly tested (`test_integrations_api.py::test_list_integrations_never_exposes_a_secret_value`), response only ever contains `name`/`purpose`/`status`/`note`, never a key |

## 5. Required credential rotation

Both Tavily and Firecrawl API keys were **present in this session's
live environment** and, per the earlier sessions' own findings,
**Tavily was actually called** (confirmed by real HTTP 432 rate-limit
responses logged during this project) before being switched off.
Firecrawl was configured as the active extraction provider but was
**not** confirmed to have been called (no Chanakya agent reached
Profile Researcher before the switch; see
`docs/FINAL_ACCEPTANCE_REPORT.md`).

Neither key was ever exposed in a git commit, a log file, a frontend
bundle, or an API response (per §4) — this is not a breach, but as a
routine precaution after any credential has been live in an assistant-
operated environment:

- **Recommended**: rotate the Tavily API key via the Tavily dashboard
  (Settings → API Keys → regenerate), update `backend/.env` yourself
  (never via chat), and confirm the old key is revoked.
- **Recommended**: rotate the Firecrawl API key similarly via the
  Firecrawl dashboard.
- Both are precautionary, not evidence-driven — no actual exposure was
  found. Your call on whether to rotate.

## 6. What this audit did not do

Did not call Tavily, Firecrawl, Gemini, BrightData, PDL, or NeverBounce
live (per the explicit "never call paid APIs during this audit" rule).
Did not inspect the `linkedinharness` reference app's own `.env`/secrets
(out of scope — it is the reference codebase, not modified or audited
for its own credential hygiene here).
