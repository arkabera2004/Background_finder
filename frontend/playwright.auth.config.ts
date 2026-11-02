import { defineConfig, devices } from "@playwright/test";

/**
 * Authenticated e2e suite — runs against the REAL dev servers (frontend
 * + backend) with the REAL Supabase project, not a placeholder/mock. This
 * is deliberately a separate config from `playwright.config.ts` (which
 * runs a `next start` build with placeholder env and starts its own
 * server) because authenticated flows need:
 *   - the actual backend API running (research submission, run polling)
 *   - the actual Supabase project (real session, real middleware checks)
 *
 * Prerequisites (see e2e/README.md):
 *   1. Backend running on :8010 (`uvicorn main:app --port 8010`)
 *   2. Frontend running on :3010 (`npm run dev`)
 *   3. E2E_EMAIL / E2E_PASSWORD set to a real test account's credentials
 *
 * This config does NOT start either server itself — unlike
 * playwright.config.ts's webServer, these are long-running dev processes
 * the developer already has up, and starting/stopping them per test run
 * would fight with normal local development.
 */
export default defineConfig({
  testDir: "./e2e/authenticated",
  fullyParallel: false,
  // Serial execution: two concurrent real research submissions both hit
  // the single backend process and the same external provider API keys
  // (Gemini/Tavily rate limits) — avoid that contention even though it
  // wasn't the actual cause of the timeout below (see that comment).
  workers: 1,
  retries: 0,
  // Root-caused live, not guessed: GeminiProvider.complete() (backend)
  // retries up to 3 total attempts (max_retries=2) on a timeout, each with
  // its own 120s httpx timeout and 1s/2s backoff between — worst case
  // ~363s for ONE synthesis call if Gemini is merely slow rather than
  // erroring (a fast 5xx falls back to rule-based almost immediately and
  // isn't the issue; a *slow* response is). Confirmed via backend logs: one
  // run fell back in ~25s after a 503, a different run — same code, same
  // test, run moments apart — was still in Gemini's retry loop past the
  // previous 260s timeout. This is real external API latency variance,
  // not a bug in the app or the test; size the timeout to outlast it
  // rather than treat the symptom.
  timeout: 450_000,
  reporter: "list",
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3010",
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "setup",
      testMatch: /auth\.setup\.ts/,
      testDir: "./e2e",
    },
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"], storageState: "e2e/.auth/user.json" },
      dependencies: ["setup"],
    },
  ],
});
