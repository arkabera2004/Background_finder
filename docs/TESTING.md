# Testing

## Backend

```bash
cd backend
.venv/bin/python -m pytest app/tests/ -q   # 156/156 passing
.venv/bin/ruff check app main.py scripts   # 0 errors
.venv/bin/mypy app main.py --ignore-missing-imports  # 0 errors
```

All tests run without network access or live credentials — stage/provider
tests use stub implementations (the exception is
`test_duckduckgo_search_is_live_and_returns_real_urls`, a deliberate live
network test for the free default search provider).

## Frontend

```bash
cd frontend
npx tsc --noEmit      # 0 errors
npx eslint src         # 0 errors, 2 benign warnings (intentional full-page nav)
npm run build           # succeeds with placeholder Supabase env vars
npx playwright test     # 7/7 passing — see e2e/README.md for exact scope
```

## CI

`.github/workflows/ci.yml` runs on every push/PR to `main`: backend
pytest + ruff + mypy + brief-schema drift check; frontend tsc + eslint +
build + Playwright. All gates are real (none weakened or skipped) — if
ruff/mypy/tests fail, CI fails.

## Chanakya (Phase 12)

The seven-agent monthly pipeline (`docs/CHANAKYA_GAP_ANALYSIS.md`,
`docs/PHASE_TRACKER.md`) has its own test files under `backend/app/tests/`,
one per agent plus three cross-cutting files:

- `test_chanakya_run_lifecycle.py` — repository-level: run/offering/
  agent-execution/evidence/company/person/email/brief/QA lifecycle,
  idempotency, retention purge.
- `test_chanakya_api.py`, `test_company_scout.py`, `test_people_finder.py`,
  `test_linkedin_resolver.py` + `_api.py`, `test_email_hunter.py` + `_api.py`,
  `test_profile_researcher.py` + `_api.py`, `test_qa_sync.py` + `_api.py` —
  one pair per agent, service-level (pure logic) and API-level (HTTP, fake
  providers).
- `test_orchestrator_api.py` — Phase 9's sequential orchestrator: stop/resume
  behavior, idempotent rerun.
- `test_chanakya_tenant_isolation.py` — 18 parametrized cross-owner 404
  checks across every agent's endpoints (Phase 11).
- `test_chanakya_end_to_end.py` — **the single full-pipeline test**: run
  creation → offering brief → orchestrate (Agents 02-07) → verify every
  agent's real output → human approval → export → idempotent rerun, all in
  one deterministic test with fake search providers. This is the "full
  end-to-end monthly pipeline using deterministic fixtures" test.

All of it is fixture-tested (fake `SearchProvider`/`EmailVerificationProvider`
implementations, no real network) — none of it has run against live
DuckDuckGo/Tavily, a real NeverBounce key, Clay, or a browser-based LinkedIn
lookup, and none of it has run against a real Supabase/Postgres instance.
That distinction is preserved honestly everywhere in `docs/PHASE_TRACKER.md`.

## What "passing" does NOT mean here

None of the above exercises a real Supabase project, real
Anthropic/Gemini/Tavily calls, or a running backend+frontend pair talking
to each other over HTTP with a live database. The Playwright suite
specifically verifies unauthenticated routing/UI only — see
`frontend/e2e/README.md`. See `docs/KNOWN_LIMITATIONS.md` for the full,
honest list.
