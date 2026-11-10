/**
 * Phase 5 M7: the interface against a real API that is slow, stopped, restarted or without its
 * database, and against a page whose code cannot be downloaded.
 *
 * Outages are real: the API container is stopped or restarted, and the browser-test database
 * refuses connections (scripts/e2e_stack.py database off). Network-level faults that cannot be
 * produced otherwise (a lost chunk download, a delayed or dropped response) are injected with
 * page.route. Every outage is ended in a finally block, so a failing test never leaves it on.
 */
import { expect, test, type Page } from "@playwright/test";

import {
  apiCall,
  createAccount,
  predictThroughApi,
  runDatabaseScript,
  setDatabaseAvailable,
  signInWith,
  startApiContainer,
  statePath,
  stopApiContainer,
  restartApiContainer,
  uniqueId,
  waitForApi,
} from "./support";

test.use({ storageState: statePath("analyst") });

/** Text an error shown to a user must never contain. */
const INTERNALS = /traceback|select |insert |psycopg|sqlalchemy|postgres|password|stack|127\.0\.0\.1|\.py\b/i;

async function expectSafeAlert(page: Page, message: RegExp | string): Promise<void> {
  const alert = page.getByRole("alert").filter({ hasText: message });
  await expect(alert).toBeVisible();
  await expect(alert).toContainText(/Reference: \S+/);
  expect(await alert.innerText()).not.toMatch(INTERNALS);
}

async function fillScoringForm(page: Page, identifier: string): Promise<void> {
  await page.getByLabel("Amount").fill("1250.00");
  await page.getByLabel("Transaction type").selectOption("PAYMENT");
  await page.getByLabel("Simulation step").fill("12");
  await page.getByLabel("Transaction identifier (optional)").fill(identifier);
}

/** Store one transaction, so the explorer has a table whatever ran before (no order dependence). */
async function ensureATransaction(page: Page): Promise<void> {
  await predictThroughApi(page, { amount: "120.00", transaction_type: "PAYMENT", step: 7, destination_category: "merchant" });
}

async function storedCount(page: Page, identifier: string): Promise<number> {
  const response = await apiCall(page, "GET", `/api/v1/transactions?external_id=${identifier}&limit=5`);
  expect(response.status()).toBe(200);
  return ((await response.json()) as { total: number }).total;
}

test("a page whose code fails to download offers a reload, and the frame stays usable", async ({ page }) => {
  await page.goto("/dashboard");
  await expect(page.getByRole("heading", { name: "Dashboard", level: 1 })).toBeVisible();
  // As after a redeploy that renamed the file, or a dropped connection.
  await page.route("**/assets/TransactionExplorerPage-*.js", (route) => route.abort("failed"));
  await page.getByRole("link", { name: "Transaction Explorer" }).click();
  await expect(page.getByRole("heading", { name: "This page could not be loaded" })).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Main navigation" })).toBeVisible();

  // Another page still works, and coming back shows the prompt again rather than a blank page.
  await page.getByRole("link", { name: "Reports" }).click();
  await expect(page.getByRole("heading", { name: "Reports", level: 1 })).toBeVisible();

  await page.unroute("**/assets/TransactionExplorerPage-*.js");
  await page.getByRole("link", { name: "Transaction Explorer" }).click();
  await page.getByRole("button", { name: "Reload" }).click();
  await expect(page.getByRole("heading", { name: "Transaction Explorer", level: 1 })).toBeVisible();
});

test("a slow answer shows the loading state, then the page", async ({ page }) => {
  await page.route("**/api/v1/reports/summary", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 2_000));
    await route.continue();
  });
  await page.goto("/dashboard");
  await expect(page.getByRole("status").filter({ hasText: "Loading" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Model flags" })).toBeVisible({ timeout: 15_000 });
  await expect(page.getByRole("alert")).toHaveCount(0);
});

test("a request with no answer says so, and Try again recovers", async ({ page }) => {
  await ensureATransaction(page);
  await page.route("**/api/v1/transactions?*", (route) => route.abort("connectionreset"));
  await page.goto("/transactions");
  const alert = page.getByRole("alert").filter({ hasText: "The server could not be reached" });
  await expect(alert).toBeVisible();
  expect(await alert.innerText()).not.toMatch(INTERNALS);
  await page.unroute("**/api/v1/transactions?*");
  await alert.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByRole("table")).toBeVisible();
});

test("while the API is stopped the app says it is unavailable, not signed out, and continues after", async ({ page }) => {
  test.setTimeout(180_000);
  stopApiContainer();
  try {
    await page.goto("/transactions");
    await expect(page.getByRole("heading", { name: "FinGuard AI is unavailable" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Sign in" })).toHaveCount(0);
    expect(await page.getByRole("alert").innerText()).not.toMatch(INTERNALS);
  } finally {
    await startApiContainer();
  }
  await page.getByRole("button", { name: "Try again" }).click();
  // The same session continues: no sign-in was needed.
  await expect(page.getByRole("heading", { name: "Transaction Explorer", level: 1 })).toBeVisible();
  await expect(page.getByRole("button", { name: "Sign out" })).toBeVisible();
});

test("a session survives an API restart in the middle of a task", async ({ page }) => {
  test.setTimeout(180_000);
  const identifier = uniqueId("RESTART");
  await page.goto("/analyse");
  await fillScoringForm(page, identifier);
  restartApiContainer();
  await waitForApi();
  await page.getByRole("button", { name: "Score transaction" }).click();
  await expect(page.getByRole("article", { name: "Prediction result" })).toBeVisible();
  expect(await storedCount(page, identifier)).toBe(1);
  await page.getByRole("link", { name: "Transaction Explorer" }).click();
  await expect(page.getByRole("heading", { name: "Transaction Explorer", level: 1 })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Sign in" })).toHaveCount(0);
});

test("a database outage gives an actionable message, keeps the session, and recovers without a restart", async ({ page }) => {
  test.setTimeout(120_000);
  await ensureATransaction(page);
  await page.goto("/reports");
  await expect(page.getByRole("heading", { name: "Reports", level: 1 })).toBeVisible();
  let downloads = 0;
  page.on("download", () => {
    downloads += 1;
  });
  setDatabaseAvailable(false);
  try {
    await page.getByRole("button", { name: "Download transaction predictions" }).click();
    await expectSafeAlert(page, "The database could not be reached. Try again in a moment");
    expect(downloads).toBe(0);

    await page.getByRole("link", { name: "Transaction Explorer" }).click();
    await expectSafeAlert(page, "The database could not be reached. Try again in a moment");
    // A 503 is not a session ending: the user is still signed in.
    await expect(page.getByRole("button", { name: "Sign out" })).toBeVisible();
  } finally {
    setDatabaseAvailable(true);
  }
  // The API reconnects on its own; no restart.
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByRole("table")).toBeVisible();
  await page.getByRole("link", { name: "Reports" }).click();
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download transaction predictions" }).click();
  expect((await download).suggestedFilename()).toBe("finguard-predictions.csv");
});

test.describe("a session ending during a task", () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test("returns to the same page after signing in again, and stores nothing meanwhile", async ({ page, browser }) => {
    const { email, password } = await createAccount(browser);
    await signInWith(page, email, password);
    const identifier = uniqueId("EXPIRED");
    await page.goto("/analyse");
    await fillScoringForm(page, identifier);
    runDatabaseScript("expire-sessions", email);

    await page.getByRole("button", { name: "Score transaction" }).click();
    await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
    await expect(page.getByRole("status")).toHaveText("Your session has ended. Please sign in again.");

    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill(password);
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page).toHaveURL(/\/analyse$/);
    await expect(page.getByRole("heading", { name: "Transaction Analysis", level: 1 })).toBeVisible();
    expect(await storedCount(page, identifier)).toBe(0);
  });
});

test("pressing Score twice stores one transaction", async ({ page }) => {
  await page.goto("/analyse");
  await fillScoringForm(page, "");
  const totalBefore = ((await (await apiCall(page, "GET", "/api/v1/transactions?limit=1")).json()) as { total: number }).total;
  const responses: number[] = [];
  page.on("response", (response) => {
    if (response.url().endsWith("/api/v1/transactions/predict")) responses.push(response.status());
  });
  await page.getByRole("button", { name: "Score transaction" }).dblclick();
  await expect(page.getByRole("article", { name: "Prediction result" })).toBeVisible();
  // Let any second request finish before counting, so a late duplicate would be seen.
  await page.waitForLoadState("networkidle");
  const totalAfter = ((await (await apiCall(page, "GET", "/api/v1/transactions?limit=1")).json()) as { total: number }).total;
  expect(responses).toEqual([201]);
  expect(totalAfter - totalBefore).toBe(1);
});
