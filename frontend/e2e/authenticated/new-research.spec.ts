import { expect, test } from "@playwright/test";

// Uses "Paste Profile Text" intake deliberately: it's the only mode that
// doesn't depend on a live LinkedIn scrape succeeding, keeping this test's
// pass/fail tied to the app's own code rather than a third-party provider's
// availability. The web-footprint/company-research stages still make real
// search calls if those providers are configured in the backend's .env —
// this is a genuine pipeline run, not a mock.

test.beforeEach(() => {
  test.skip(
    !process.env.E2E_EMAIL || !process.env.E2E_PASSWORD,
    "Set E2E_EMAIL/E2E_PASSWORD to run the authenticated e2e suite. See e2e/README.md."
  );
});

test("submitting pasted profile text runs the pipeline to completion", async ({ page }) => {
  await page.goto("/research/new");

  await page.getByRole("button", { name: "Paste Profile Text" }).click();

  const uniqueName = `Playwright Test Subject ${Date.now()}`;
  await page.getByLabel("Full name").fill(uniqueName);
  await page
    .getByLabel(/pasted profile text/i)
    .fill(
      `${uniqueName} is a Senior Engineer at Acme Testing Co, based in a fictional city. ` +
        "This profile text exists only to drive an automated end-to-end test."
    );

  await page.getByRole("button", { name: "Start Research" }).click();

  await expect(page).toHaveURL(/\/runs\/[0-9a-f-]+$/, { timeout: 15_000 });

  // Pipeline progress card: proper-case status labels and an N/total·%
  // summary should appear immediately, before the run finishes.
  await expect(page.getByText(/^\d+\/\d+ · \d+%$/)).toBeVisible();

  // Each of the 7 pipeline steps gets its own "Completed" badge as it
  // finishes, long before the run as a whole is done — matching on that
  // text alone (even .first()) resolves almost immediately and proves
  // nothing. "Save to Prospect Library" only renders once
  // run.status === "completed" && run.brief, so it's the real signal.
  // The run completes via the rule-based fallback if no AI provider is
  // configured/reachable, or via a real (slow) AI call otherwise — either
  // way it must reach this terminal, brief-rendered state.
  await expect(page.getByRole("button", { name: "Save to Prospect Library" })).toBeVisible({
    timeout: 260_000,
  });
  await expect(page.getByText(`Prospect Brief: ${uniqueName}`)).toBeVisible();
  // Section titles render as plain styled <div>s (CardTitle), not <h*>
  // elements, so these are text matches, not heading-role matches.
  await expect(page.getByText("Identity Verification", { exact: true })).toBeVisible();
});
