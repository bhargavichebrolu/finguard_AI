/**
 * Report downloads, and Settings: the high risk boundary, password changes and account
 * management, each checked against what the API then does.
 */
import { readFileSync } from "node:fs";

import { expect, test, type Browser, type Page } from "@playwright/test";

import {
  NO_SESSION,
  account,
  apiCall,
  predictThroughApi,
  repoFile,
  signInThroughForm,
  startSession,
  statePath,
  uniqueId,
} from "./support";

async function downloadReport(page: Page, button: string): Promise<{ name: string; lines: string[] }> {
  const pending = page.waitForEvent("download");
  await page.getByRole("button", { name: button }).click();
  const file = await pending;
  return { name: file.suggestedFilename(), lines: readFileSync((await file.path())!, "utf-8").trim().split(/\r?\n/) };
}

test.describe("reports", () => {
  test.use({ storageState: statePath("analyst") });

  test("downloads all four reports with their saved contents", async ({ page }) => {
    await page.goto("/reports");
    await predictThroughApi(page, { amount: "120.00", transaction_type: "PAYMENT", step: 7, destination_category: "merchant" });

    const predictions = await downloadReport(page, "Download transaction predictions");
    expect(predictions.name).toBe("finguard-predictions.csv");
    expect(predictions.lines[0]).toContain("model_score,score_is_calibrated");
    expect(predictions.lines[0]).not.toMatch(/is_fraud|isFraud|label/);
    expect(predictions.lines.length).toBeGreaterThan(1);

    const summary = await downloadReport(page, "Download flag summary");
    expect(summary.name).toBe("finguard-flag_summary.csv");
    expect(summary.lines[0]).toBe("transaction_type,analysed,flagged_for_review");
    const analysed = summary.lines.slice(1).reduce((total, line) => total + Number(line.split(",")[1]), 0);
    const stored = (await (await apiCall(page, "GET", "/api/v1/transactions?limit=1")).json()) as { total: number };
    expect(analysed).toBe(stored.total);

    const investigations = await downloadReport(page, "Download investigation summary");
    expect(investigations.name).toBe("finguard-investigations.csv");
    expect(investigations.lines[0]).toBe("investigation_id,external_transaction_id,workflow_status,assigned_user_id,model_score,risk_level,created_at,updated_at");

    const evaluation = await downloadReport(page, "Download model evaluation");
    expect(evaluation.name).toBe("finguard-model_evaluation.csv");
    expect(evaluation.lines[0]).toBe("partition,slice,metric,value");
    const metrics = JSON.parse(repoFile("artifacts/metadata/model_v1_metrics.json"));
    const rows = evaluation.lines.slice(1).map((line) => line.split(","));
    const partitions = new Set(rows.map((row) => row[0]));
    expect(partitions.has("validation") && partitions.has("test")).toBe(true);
    const testRecall = rows.find((row) => row[0] === "test" && row[2] === "recall");
    expect(testRecall, "test recall row").toBeDefined();
    expect(Number(testRecall![3])).toBeCloseTo(metrics.test.at_frozen_threshold.recall, 12);
  });

  test("demo users cannot export", async ({ browser }) => {
    const context = await browser.newContext({ storageState: statePath("demo") });
    const page = await context.newPage();
    await page.goto("/reports");
    await expect(page.getByRole("heading", { name: "Not available for your role" })).toBeVisible();
    expect((await apiCall(page, "GET", "/api/v1/reports/export?report_type=model_evaluation")).status()).toBe(403);
    await context.close();
  });
});

test.describe("high risk boundary", () => {
  test.use({ storageState: statePath("admin") });

  test("an administrator changes it after confirming, and new predictions use it", async ({ page }) => {
    await page.goto("/settings");
    const settings = (await (await apiCall(page, "GET", "/api/v1/settings")).json()) as { high_risk_boundary: number; frozen_threshold: number };
    const original = settings.high_risk_boundary;
    const field = page.getByLabel("High risk boundary");

    try {
      await field.fill("0.01");
      await page.getByRole("button", { name: "Save boundary" }).click();
      await expect(page.getByText(/Enter a value above the frozen threshold/)).toBeVisible();
      await expect(page.getByRole("dialog")).toHaveCount(0);

      await field.fill("0.5");
      await page.getByRole("button", { name: "Save boundary" }).click();
      await page.getByRole("dialog").getByRole("button", { name: "Cancel" }).click();
      expect(((await (await apiCall(page, "GET", "/api/v1/settings")).json()) as { high_risk_boundary: number }).high_risk_boundary).toBe(original);

      await page.getByRole("button", { name: "Save boundary" }).click();
      await page.getByRole("dialog").getByRole("button", { name: "Change boundary" }).click();
      await expect(page.getByText(/^Saved\./)).toBeVisible();
      await page.reload();
      await expect(page.locator("dl.facts").first()).toContainText("High risk boundary0.5000");

      // A score of about 0.44 is High under 0.3 and Medium under 0.5. The flag itself never moves.
      const scored = await predictThroughApi(page, { amount: "1000000.00", transaction_type: "TRANSFER", step: 3, destination_category: "customer" });
      expect(scored.high_risk_boundary_used).toBe(0.5);
      expect(scored.model_score).toBeLessThan(0.5);
      expect(scored.risk_level).toBe("MEDIUM");
      expect(scored.prediction).toBe("FLAG_FOR_REVIEW");
      expect(scored.threshold_used).toBe(settings.frozen_threshold);

      const audit = (await (await apiCall(page, "GET", "/api/v1/audit-logs?limit=50")).json()) as { items: { action: string }[] };
      expect(audit.items.some((entry) => entry.action.startsWith("settings."))).toBe(true);
    } finally {
      expect((await apiCall(page, "PATCH", "/api/v1/settings", { high_risk_boundary: original })).status()).toBe(200);
    }
  });
});

test.describe("password change", () => {
  test.use({ storageState: NO_SESSION });

  test("signs the user out everywhere, and only the new password then works", async ({ page }) => {
    const { email, password } = account("password");
    const replacement = `New-${uniqueId("p")}-${uniqueId("q")}`;
    await signInThroughForm(page, "password");
    await page.goto("/settings");
    await page.getByLabel("Current password").fill(password);
    await page.getByLabel("New password").fill("short");
    await expect(page.getByRole("button", { name: "Change password" })).toBeDisabled();
    await page.getByLabel("New password").fill(replacement);
    await page.getByRole("button", { name: "Change password" }).click();
    await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();

    expect((await startSession(page, email, password)).status()).toBe(401);
    expect((await startSession(page, email, replacement)).status()).toBe(200);
  });
});

async function signedInAs(browser: Browser, email: string, password: string): Promise<Page> {
  const context = await browser.newContext({ storageState: NO_SESSION });
  const page = await context.newPage();
  await page.goto("/login");
  expect((await startSession(page, email, password)).status()).toBe(200);
  return page;
}

test.describe("account management", () => {
  test.use({ storageState: statePath("admin") });

  test("creates an account and changes its role", async ({ page, browser }) => {
    const email = `new-${uniqueId("u").toLowerCase()}@e2e.example.com`;
    const password = `Pw-${uniqueId("x")}-${uniqueId("y")}`;
    await page.goto("/settings");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Temporary password").fill(password);
    await page.getByLabel("Role", { exact: true }).selectOption("analyst");
    await page.getByRole("button", { name: "Create account" }).click();
    await expect(page.getByText(`Created ${email}. Share the temporary password privately.`)).toBeVisible();
    const row = page.getByRole("table", { name: "Accounts" }).getByRole("row", { name: new RegExp(email) });
    await expect(row).toBeVisible();

    const newUser = await signedInAs(browser, email, password);
    expect(((await (await apiCall(newUser, "GET", "/api/v1/auth/me")).json()) as { role: string }).role).toBe("analyst");

    await page.getByLabel(`Role for ${email}`).selectOption("investigator");
    await expect(page.getByLabel(`Role for ${email}`)).toHaveValue("investigator");
    // Roles are read per request, so the open session gains the permission at once.
    const after = (await (await apiCall(newUser, "GET", "/api/v1/auth/me")).json()) as { role: string; permissions: string[] };
    expect(after.role).toBe("investigator");
    expect(after.permissions).toContain("update_investigations");
    await newUser.context().close();
  });

  test("deactivates another account after confirming, ending its live session", async ({ page, browser }) => {
    const { email, password } = account("deactivate");
    const target = await signedInAs(browser, email, password);
    expect((await apiCall(target, "GET", "/api/v1/auth/me")).status()).toBe(200);

    await page.goto("/settings");
    const row = page.getByRole("table", { name: "Accounts" }).getByRole("row", { name: new RegExp(email) });
    await row.getByRole("button", { name: "Deactivate" }).click();
    const dialog = page.getByRole("dialog", { name: `Deactivate ${email}?` });
    await dialog.getByRole("button", { name: "Cancel" }).click();
    await expect(row).toContainText("Yes");

    await row.getByRole("button", { name: "Deactivate" }).click();
    await page.getByRole("dialog").getByRole("button", { name: "Deactivate" }).click();
    await expect(row.getByRole("button", { name: "Reactivate" })).toBeVisible();
    await expect(row).toContainText("No");

    expect((await apiCall(target, "GET", "/api/v1/auth/me")).status()).toBe(401);
    expect((await startSession(target, email, password)).status()).toBe(401);
    await target.context().close();
  });

  test("an administrator cannot deactivate their own account, in the interface or the API", async ({ page }) => {
    const admin = account("admin");
    await page.goto("/settings");
    const own = page.getByRole("table", { name: "Accounts" }).getByRole("row", { name: new RegExp(admin.email) });
    await expect(own.getByRole("button", { name: "Deactivate" })).toBeDisabled();

    const me = (await (await apiCall(page, "GET", "/api/v1/auth/me")).json()) as { id: string };
    const refused = await apiCall(page, "PATCH", `/api/v1/users/${me.id}`, { is_active: false });
    expect(refused.status()).toBe(422);
    expect((await refused.json()).detail).toBe("You cannot deactivate your own account.");
    expect((await apiCall(page, "GET", "/api/v1/auth/me")).status()).toBe(200);
  });
});
