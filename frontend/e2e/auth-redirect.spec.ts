import { expect, test } from "@playwright/test";

// These run against a real `next start` build with placeholder Supabase
// credentials (no live project). They verify the server-side auth
// middleware actually redirects, not a mock. See e2e/README.md.

const PROTECTED_ROUTES = ["/dashboard", "/prospects", "/companies", "/research/new", "/settings"];

for (const route of PROTECTED_ROUTES) {
  test(`unauthenticated visit to ${route} redirects to /login`, async ({ page }) => {
    await page.goto(route);
    await expect(page).toHaveURL(/\/login$/);
  });
}

test("login page renders the sign-in form", async ({ page }) => {
  await page.goto("/login");

  await expect(page.getByText(/sign in to prospectlens/i)).toBeVisible();
  await expect(page.getByLabel("Email")).toBeVisible();
  await expect(page.getByLabel("Password")).toBeVisible();
  await expect(page.getByRole("button", { name: /^sign in$/i })).toBeVisible();
  await expect(page.getByRole("button", { name: /continue with google/i })).toBeVisible();
});

test("login form requires email and password before submit", async ({ page }) => {
  await page.goto("/login");

  await page.getByRole("button", { name: /^sign in$/i }).click();

  // Native HTML required-field validation blocks submission — still on /login.
  await expect(page).toHaveURL(/\/login$/);
  const emailValidity = await page.getByLabel("Email").evaluate(
    (el: HTMLInputElement) => el.validity.valid,
  );
  expect(emailValidity).toBe(false);
});
