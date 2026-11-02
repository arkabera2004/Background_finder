import { expect, test } from "@playwright/test";

// Authenticated session is already loaded via e2e/auth.setup.ts's saved
// storage state (see playwright.auth.config.ts) — these are real pages
// served by the real backend, not mocks.

test.beforeEach(() => {
  test.skip(
    !process.env.E2E_EMAIL || !process.env.E2E_PASSWORD,
    "Set E2E_EMAIL/E2E_PASSWORD to run the authenticated e2e suite. See e2e/README.md."
  );
});

test("dashboard loads for an authenticated session", async ({ page }) => {
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/dashboard$/);
  // Sidebar is the one piece of chrome present on every authenticated page.
  await expect(page.getByRole("link", { name: "New Research" })).toBeVisible();
});

test("sidebar navigates between Dashboard, Prospects, and Companies", async ({ page }) => {
  await page.goto("/dashboard");

  await page.getByRole("link", { name: "Prospects" }).click();
  await expect(page).toHaveURL(/\/prospects$/);

  await page.getByRole("link", { name: "Companies" }).click();
  await expect(page).toHaveURL(/\/companies$/);

  await page.getByRole("link", { name: "Dashboard" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
});

test("new research page renders all three intake modes", async ({ page }) => {
  await page.goto("/research/new");

  await expect(page.getByRole("button", { name: "LinkedIn URL" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Name + Company" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Paste Profile Text" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Start Research" })).toBeVisible();
});
