# E2E tests — scope and honesty notes

Two separate suites, two separate configs, because they verify genuinely
different things and have different prerequisites.

## 1. Unauthenticated suite — `npm run test:e2e`

Config: `playwright.config.ts`. Runs against a real `next start` production
build with **placeholder** Supabase credentials — no real Supabase project,
no real backend API, no real authenticated session. Starts its own server.

Verifies:

- Unauthenticated requests to every protected route (`/dashboard`,
  `/prospects`, `/companies`, `/research/new`, `/settings`) are redirected
  by the real Next.js middleware (`src/lib/supabase/middleware.ts`) to
  `/login` — this exercises actual server-side routing code, not a mock.
- The `/login` page renders its real form and client-side validation.

No setup required; run it any time.

## 2. Authenticated suite — `npm run test:e2e:auth`

Config: `playwright.auth.config.ts`. Runs against the **real** dev
servers and the **real** Supabase project — a genuine login, a genuine
research pipeline run, genuine persistence. Nothing here is mocked.

### Prerequisites

1. Backend running: `cd backend && uvicorn main:app --host 127.0.0.1 --port 8010`
2. Frontend running: `cd frontend && npm run dev` (defaults to :3010)
3. A real test account's credentials, exported as environment variables:

   ```sh
   export E2E_EMAIL="your-test-account@example.com"
   export E2E_PASSWORD="..."
   npm run test:e2e:auth
   ```

   If these aren't set, `e2e/auth.setup.ts` skips itself (and therefore
   every authenticated spec that depends on it) with a clear message
   instead of failing — same pattern the backend uses for missing
   provider API keys.

4. Optional: `E2E_BASE_URL` to point at something other than
   `http://localhost:3010`.

### What this verifies

- `e2e/auth.setup.ts` — a real `signInWithPassword` call against Supabase,
  reused across every spec in this suite via saved storage state
  (`e2e/.auth/user.json`, gitignored — it holds a live session token).
- `authenticated/navigation.spec.ts` — dashboard loads, sidebar nav
  between Dashboard/Prospects/Companies, New Research page renders all
  three intake modes.
- `authenticated/new-research.spec.ts` — submits via Paste Profile Text
  (the only intake mode that doesn't depend on a live LinkedIn scrape
  succeeding), follows the real run through the real backend pipeline to
  a terminal "Completed" state, and checks the rendered brief.
- `authenticated/prospect-library.spec.ts` — saves a completed run,
  confirms it appears in the prospect list, and confirms the Markdown
  export button actually triggers a file download.

### What this does NOT verify

- The LinkedIn-URL and Name+Company intake modes aren't exercised here —
  they depend on live Bright Data/search provider calls whose success
  isn't something this test suite controls or should gate on.
- AI-backed synthesis: whichever path the backend actually takes (AI or
  rule-based fallback) is accepted: the suite asserts the run reaches
  "Completed" and renders a brief, not which synthesis path produced it.
- PDF export's byte content isn't inspected, only that clicking it is
  wired up without throwing (same standard as Markdown's filename check).

## CI

The unauthenticated suite runs on every push/PR (`.github/workflows/ci.yml`,
`frontend` job). The authenticated suite has its own job (`e2e-auth`) but
is **manual-only** — triggered from the Actions tab (`workflow_dispatch`),
never automatically — because it hits real external APIs (Tavily, Gemini)
that cost money and take minutes per run. See that job's comments in
`ci.yml` for the required repo secrets.
