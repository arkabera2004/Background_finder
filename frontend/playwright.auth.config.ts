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
  retries: 0,
  timeout: 180_000, // research submission involves a real Bright Data + AI call
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
