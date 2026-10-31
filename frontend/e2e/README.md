# E2E tests — scope and honesty notes

These Playwright tests run against a real `next start` production build
(see `playwright.config.ts`) with **placeholder** Supabase credentials —
there is no real Supabase project, no real backend API, and no real
authenticated session anywhere in this suite.

## What IS verified here (live, against the built app)

- Unauthenticated requests to every protected route (`/dashboard`,
  `/prospects`, `/companies`, `/research/new`, `/settings`) are redirected
  by the real Next.js middleware (`src/lib/supabase/middleware.ts`) to
  `/login` — this exercises actual server-side routing code, not a mock.
- The `/login` page renders its real form (email, password, submit,
  Google OAuth button) and client-side validation (empty submit is
  blocked by the `required` attributes).

## What is NOT verified here

Everything that requires an authenticated session — the research form
submit → run polling, identity disambiguation, save-to-prospect, brief
export, companies/prospects data pages — needs a real Supabase session
(the middleware calls `supabase.auth.getUser()` server-side; there is no
practical way to forge that without either a live Supabase project or
rewriting the auth layer to be test-injectable, which is out of scope
here). Those flows remain covered only by backend fixture tests
(`backend/app/tests/`) and manual `curl`/browser verification, as
documented in `docs/PHASE_TRACKER.md` and `docs/KNOWN_LIMITATIONS.md`.

Do not read a passing run of this suite as proof that login, research
intake, or any authenticated page works end-to-end against a real
backend — it is not.
