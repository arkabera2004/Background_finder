import { expect, test } from "@playwright/test";

test.beforeEach(() => {
  test.skip(
    !process.env.E2E_EMAIL || !process.env.E2E_PASSWORD,
    "Set E2E_EMAIL/E2E_PASSWORD to run the authenticated e2e suite. See e2e/README.md."
  );
});

test("saving a completed run creates a prospect with working exports", async ({ page }) => {
  await page.goto("/research/new");
  await page.getByRole("button", { name: "Paste Profile Text" }).click();

  const uniqueName = `Playwright Export Test ${Date.now()}`;
  await page.getByLabel("Full name").fill(uniqueName);
  await page
    .getByLabel(/pasted profile text/i)
    .fill(
      `${uniqueName} is a Product Manager at a fictional testing company. ` +
        "This profile text exists only to drive an automated end-to-end test."
    );
  await page.getByRole("button", { name: "Start Research" }).click();

  await expect(page).toHaveURL(/\/runs\/[0-9a-f-]+$/, { timeout: 15_000 });
  await expect(page.getByText("Completed", { exact: true }).first()).toBeVisible({
    timeout: 170_000,
  });

  await page.getByRole("button", { name: "Save to Prospect Library" }).click();
  await expect(page).toHaveURL(/\/prospects\/[0-9a-f-]+$/, { timeout: 15_000 });
  await expect(page.getByText(uniqueName).first()).toBeVisible();

  // Export buttons must be present and enabled — not a claim they produce
  // a byte-perfect file, just that the UI wiring to request an export
  // works without throwing.
  const exportMarkdown = page.getByRole("button", { name: "Export Markdown" });
  await expect(exportMarkdown).toBeVisible();
  await expect(exportMarkdown).toBeEnabled();
  const exportPdf = page.getByRole("button", { name: "Export PDF" });
  await expect(exportPdf).toBeVisible();
  await expect(exportPdf).toBeEnabled();

  const [download] = await Promise.all([page.waitForEvent("download"), exportMarkdown.click()]);
  expect(download.suggestedFilename()).toMatch(/\.(md|markdown)$/i);

  // Prospect must also show up in the list view.
  await page.goto("/prospects");
  await expect(page.getByText(uniqueName).first()).toBeVisible();
});
