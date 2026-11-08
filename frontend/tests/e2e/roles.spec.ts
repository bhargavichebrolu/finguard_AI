/**
 * Each role sees only its pages and controls, and the API refuses the rest on its own: every
 * refusal below is checked by calling the API directly, bypassing the interface.
 */
import { expect, test, type Page } from "@playwright/test";

import { FLAGGED_INPUT, apiCall, predictThroughApi, statePath, type AccountName } from "./support";

const ALL_PAGES = [
  "Dashboard",
  "Transaction Analysis",
  "CSV Batch Analysis",
  "Transaction Explorer",
  "Investigation Centre",
  "Model Performance",
  "Explainable AI",
  "Reports",
  "Settings",
  "System Information",
];
const DEMO_PAGES = ALL_PAGES.filter((name) => name !== "Investigation Centre" && name !== "Reports");

const EXPECTED_NAVIGATION: Record<string, string[]> = {
  demo: DEMO_PAGES,
  analyst: ALL_PAGES,
  investigator: ALL_PAGES,
  admin: ALL_PAGES,
};

async function navigationLabels(page: Page): Promise<string[]> {
  const navigation = page.getByRole("navigation", { name: "Main navigation" });
  return navigation.getByRole("link").allInnerTexts().then((labels) => labels.map((label) => label.trim()));
}

for (const role of ["demo", "analyst", "investigator", "admin"] as AccountName[]) {
  test.describe(`${role} role`, () => {
    test.use({ storageState: statePath(role) });

    test("navigation lists exactly the permitted pages, in PRD order", async ({ page }) => {
      await page.goto("/");
      await expect(page.getByRole("heading", { name: "Dashboard", level: 1 })).toBeVisible();
      expect(await navigationLabels(page)).toEqual(EXPECTED_NAVIGATION[role]);
    });
  });
}

test.describe("demo role", () => {
  test.use({ storageState: statePath("demo") });

  test("cannot open restricted pages by address", async ({ page }) => {
    for (const path of ["/investigations", "/reports"]) {
      await page.goto(path);
      await expect(page.getByRole("heading", { name: "Not available for your role" })).toBeVisible();
    }
  });

  test("is refused by the API whatever the interface shows", async ({ page }) => {
    await page.goto("/dashboard");
    expect((await apiCall(page, "GET", "/api/v1/investigations")).status()).toBe(403);
    expect((await apiCall(page, "GET", "/api/v1/reports/export?report_type=predictions")).status()).toBe(403);
    expect((await apiCall(page, "PATCH", "/api/v1/settings", { high_risk_boundary: 0.5 })).status()).toBe(403);
    expect((await apiCall(page, "GET", "/api/v1/users")).status()).toBe(403);
    expect((await apiCall(page, "GET", "/api/v1/audit-logs")).status()).toBe(403);
  });

  test("demo records are kept apart from other users' records", async ({ page, browser }) => {
    await page.goto("/dashboard");
    const demo = await predictThroughApi(page, FLAGGED_INPUT);
    expect(demo.is_demo).toBe(true);
    expect(demo.investigation_id).toBeNull();

    const analyst = await browser.newContext({ storageState: statePath("analyst") });
    const analystPage = await analyst.newPage();
    const search = await apiCall(analystPage, "GET", `/api/v1/transactions?external_id=${demo.external_transaction_id}`);
    expect(search.status()).toBe(200);
    expect((await search.json()).total).toBe(0);
    expect((await apiCall(analystPage, "GET", `/api/v1/transactions/${demo.transaction_id}`)).status()).toBe(404);
    await analyst.close();
  });
});

test.describe("analyst role", () => {
  test.use({ storageState: statePath("analyst") });

  test("can view but not change investigations, settings or accounts", async ({ page }) => {
    await page.goto("/dashboard");
    const flagged = await predictThroughApi(page, FLAGGED_INPUT);
    expect(flagged.investigation_id).not.toBeNull();

    await page.goto(`/investigations?open=${flagged.investigation_id}`);
    await expect(page.getByText("You can view investigations. Investigators and administrators can change them.")).toBeVisible();
    await expect(page.getByRole("button", { name: "Update status" })).toHaveCount(0);
    await expect(page.getByLabel("Add a note")).toHaveCount(0);

    await page.goto("/settings");
    await expect(page.getByRole("heading", { name: "Risk bands" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Change the high risk boundary" })).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Accounts" })).toHaveCount(0);

    await page.goto("/system");
    await expect(page.getByRole("heading", { name: "Service" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Audit log" })).toHaveCount(0);

    const id = flagged.investigation_id!;
    expect((await apiCall(page, "PATCH", `/api/v1/investigations/${id}`, { status: "CLOSED" })).status()).toBe(403);
    expect((await apiCall(page, "POST", `/api/v1/investigations/${id}/notes`, { note: "x" })).status()).toBe(403);
    expect((await apiCall(page, "GET", "/api/v1/users/assignable")).status()).toBe(403);
    expect((await apiCall(page, "PATCH", "/api/v1/settings", { high_risk_boundary: 0.5 })).status()).toBe(403);
    expect((await apiCall(page, "GET", "/api/v1/users")).status()).toBe(403);
    expect((await apiCall(page, "POST", "/api/v1/users", { email: "x@example.com", password: "a-long-password-1", role: "admin" })).status()).toBe(403);
    expect((await apiCall(page, "GET", "/api/v1/audit-logs")).status()).toBe(403);
    expect((await apiCall(page, "GET", "/api/v1/reports/export?report_type=predictions")).status()).toBe(200);
  });
});

test.describe("investigator role", () => {
  test.use({ storageState: statePath("investigator") });

  test("can work investigations but not change settings or accounts", async ({ page }) => {
    await page.goto("/settings");
    await expect(page.getByRole("heading", { name: "Risk bands" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Change the high risk boundary" })).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Accounts" })).toHaveCount(0);

    const flagged = await predictThroughApi(page, FLAGGED_INPUT);
    const id = flagged.investigation_id!;
    expect((await apiCall(page, "PATCH", `/api/v1/investigations/${id}`, { status: "UNDER_REVIEW" })).status()).toBe(200);
    expect((await apiCall(page, "GET", "/api/v1/users/assignable")).status()).toBe(200);
    expect((await apiCall(page, "PATCH", "/api/v1/settings", { high_risk_boundary: 0.5 })).status()).toBe(403);
    expect((await apiCall(page, "GET", "/api/v1/users")).status()).toBe(403);
    expect((await apiCall(page, "PATCH", `/api/v1/users/${flagged.transaction_id}`, { is_active: false })).status()).toBe(403);
    expect((await apiCall(page, "GET", "/api/v1/audit-logs")).status()).toBe(403);
  });
});

test.describe("administrator role", () => {
  test.use({ storageState: statePath("admin") });

  test("can open account management and the audit log", async ({ page }) => {
    await page.goto("/settings");
    await expect(page.getByRole("heading", { name: "Accounts" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Change the high risk boundary" })).toBeVisible();
    await page.goto("/system");
    await expect(page.getByRole("heading", { name: "Audit log" })).toBeVisible();
    expect((await apiCall(page, "GET", "/api/v1/users")).status()).toBe(200);
    expect((await apiCall(page, "GET", "/api/v1/audit-logs")).status()).toBe(200);
  });
});
