# Testing

## Backend

```bash
cd backend
.venv/bin/python -m pytest app/tests/ -q
```

Current status: **24/24 passing** (JWT auth: 3, research input schemas: 10,
pipeline orchestrator: 4, provider abstraction: 7). All tests run without
network access or live credentials — stage/provider tests use stub
implementations. No test suite exists yet for endpoints that don't exist
yet (research intake API, stage implementations, brief synthesis).

Ruff/mypy are listed in `requirements.txt` but have not been run as a gate
yet — add to CI before Phase 7.

## Frontend

```bash
cd frontend
npx tsc --noEmit      # 0 errors
npx eslint src         # 0 errors, 2 benign warnings (intentional full-page nav)
npm run build           # succeeds with placeholder Supabase env vars
```

No component tests or Playwright E2E exist yet — Phase 7 scope.

## What "passing" does NOT mean here

None of the above exercises a real Supabase project, real Anthropic/Tavily
calls, or a running backend+frontend pair talking to each other over HTTP.
See `docs/KNOWN_LIMITATIONS.md`.
