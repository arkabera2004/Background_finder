import { expect, test as setup } from "@playwright/test";

/**
 * Logs in once with a real Supabase session and saves the storage state
 * for every authenticated spec to reuse (via `playwright.auth.config.ts`'s
 * `dependencies: ["setup"]`). Requires E2E_EMAIL/E2E_PASSWORD for a real
 * test account in the project's actual Supabase instance — there is no
 * mock here, this is a genuine login.
 *
 * If the credentials aren't set, this (and therefore every test that
 * depends on it) is skipped with a clear reason rather than failing —
 * same "honest degradation" pattern the rest of this codebase uses for
 * missing config.
 */
const AUTH_FILE = "e2e/.auth/user.json";

setup("authenticate", async ({ page }) => {
  const email = process.env.E2E_EMAIL;
  const password = process.env.E2E_PASSWORD;

  if (!email || !password) {
    // Playwright's project `dependencies` only auto-skip a dependent spec
    // when the setup project *fails* — a `test.skip()` here otherwise
    // still leaves every dependent spec unable to load its storageState
    // fixture (ENOENT) and reporting a hard failure, not "skipped". So:
    // always write a valid (empty) storage state first, so fixture setup
    // never errors, then each authenticated spec does its own
    // `test.skip()` check as its first line before touching a real page.
    await page.context().storageState({ path: AUTH_FILE });
    setup.skip(
      true,
      "Set E2E_EMAIL and E2E_PASSWORD (a real test account in this project's Supabase " +
        "instance) to run the authenticated e2e suite. See e2e/README.md."
    );
    return;
  }

  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: /^sign in$/i }).click();

  await expect(page).toHaveURL(/\/dashboard$/, { timeout: 15_000 });
  await page.context().storageState({ path: AUTH_FILE });
});
