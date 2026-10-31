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

## What "passing" does NOT mean here

None of the above exercises a real Supabase project, real
Anthropic/Gemini/Tavily calls, or a running backend+frontend pair talking
to each other over HTTP with a live database. The Playwright suite
specifically verifies unauthenticated routing/UI only — see
`frontend/e2e/README.md`. See `docs/KNOWN_LIMITATIONS.md` for the full,
honest list.
