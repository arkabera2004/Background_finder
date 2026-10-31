import { defineConfig, devices } from "@playwright/test";

/**
 * Runs against a `next start` production server with placeholder Supabase
 * env vars — no real Supabase project or backend is required for these
 * tests. They verify unauthenticated routing/UI only, not live auth or API
 * calls. See frontend/e2e/README.md for exact scope.
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: "http://localhost:3100",
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "npm run start -- -p 3100",
    url: "http://localhost:3100/login",
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
