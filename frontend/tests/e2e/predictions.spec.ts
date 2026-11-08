/**
 * Scoring one transaction: client and server validation, the score as an uncalibrated number,
 * the wording around it, the disclosed limitations, and the stored record in the explorer.
 */
import { expect, test, type Page } from "@playwright/test";

import {
  FLAGGED_INPUT,
  UNFLAGGED_INPUT,
  apiCall,
  predictThroughApi,
  repoFile,
  statePath,
  uniqueId,
  watchForProblems,
  type StoredPrediction,
} from "./support";

test.use({ storageState: statePath("analyst") });

/** Every sentence that mentions probability, chance or likelihood must deny it. */
async function expectNoProbabilityClaims(page: Page): Promise<void> {
  const text = await page.locator("body").innerText();
  const sentences = text.split(/(?<=[.!?])\s+|\n+/);
  const claims = sentences.filter((sentence) => /probabilit|likelihood|chance/i.test(sentence) && !/\bnot\b|\bnever\b/i.test(sentence));
  expect(claims).toEqual([]);
}

async function fillForm(page: Page, values: { amount: string; type: string; step: string; id?: string }) {
  await page.getByLabel("Amount").fill(values.amount);
  await page.getByLabel("Transaction type").selectOption(values.type);
  await page.getByLabel("Simulation step").fill(values.step);
  await page.getByLabel("Transaction identifier (optional)").fill(values.id ?? "");
}

async function scoreThroughForm(page: Page, values: { amount: string; type: string; step: string; id: string }): Promise<StoredPrediction> {
  await fillForm(page, values);
  const response = page.waitForResponse((r) => r.url().endsWith("/api/v1/transactions/predict") && r.request().method() === "POST");
  await page.getByRole("button", { name: "Score transaction" }).click();
  const answer = await response;
  expect(answer.status()).toBe(201);
  return (await answer.json()) as StoredPrediction;
}

test("refuses invalid inputs with field messages, without calling the API", async ({ page }) => {
  let predictCalls = 0;
  page.on("request", (request) => {
    if (request.url().endsWith("/transactions/predict")) predictCalls += 1;
  });
  await page.goto("/analyse");
  await page.getByRole("button", { name: "Score transaction" }).click();
  await expect(page.getByText("Enter an amount above 0 with at most two decimal places.")).toBeVisible();
  await expect(page.getByText("Enter a whole step from 1 to 1,000,000.")).toBeVisible();
  await expect(page.getByLabel("Amount")).toHaveAttribute("aria-invalid", "true");

  for (const [amount, step, id] of [["-5", "1", ""], ["1.234", "1", ""], ["10", "0", ""], ["10", "1.5", ""], ["10", "1", "bad id!"]]) {
    await fillForm(page, { amount, type: "TRANSFER", step, id });
    await page.getByRole("button", { name: "Score transaction" }).click();
    await expect(page.locator(".error-text").first()).toBeVisible();
  }
  await expect(page.getByText(/Use up to 64 letters, digits/)).toBeVisible();
  expect(predictCalls).toBe(0);
});

test("shows the API's own refusals", async ({ page }) => {
  await page.goto("/analyse");
  const existing = await predictThroughApi(page, UNFLAGGED_INPUT);
  await fillForm(page, { amount: "100.00", type: "TRANSFER", step: "10", id: existing.external_transaction_id });
  await page.getByRole("button", { name: "Score transaction" }).click();
  await expect(page.getByText("A transaction with this identifier already exists.")).toBeVisible();

  // The interface cannot send these, so the API is called directly to prove it checks them too.
  const mismatched = await apiCall(page, "POST", "/api/v1/transactions/predict", { ...UNFLAGGED_INPUT, destination_category: "merchant" });
  expect(mismatched.status()).toBe(422);
  const zero = await apiCall(page, "POST", "/api/v1/transactions/predict", { ...UNFLAGGED_INPUT, amount: "0" });
  expect(zero.status()).toBe(422);
  const extra = await apiCall(page, "POST", "/api/v1/transactions/predict", { ...UNFLAGGED_INPUT, isFraud: 1 });
  expect(extra.status()).toBe(422);
});

test("presents a flagged score as an uncalibrated number with its settings", async ({ page }) => {
  const problems = await watchForProblems(page);
  const metadata = JSON.parse(repoFile("artifacts/metadata/model_v1.json")) as { threshold: { value: number } };
  const threshold = metadata.threshold.value;
  await page.goto("/analyse");
  const id = uniqueId("E2E-FLAG");
  const stored = await scoreThroughForm(page, { amount: FLAGGED_INPUT.amount, type: "CASH_OUT", step: "50", id });

  expect(stored.prediction).toBe("FLAG_FOR_REVIEW");
  expect(stored.threshold_used).toBe(threshold);
  const result = page.getByRole("article", { name: "Prediction result" });
  await expect(result.getByText("Flagged for review")).toBeVisible();
  await expect(result.getByText("Model score (uncalibrated)")).toBeVisible();
  await expect(result.locator("dd.score")).toHaveText(stored.model_score.toFixed(4));
  await expect(result.getByText(/\(score × 100, not a percentage\)/)).toBeVisible();
  await expect(result.getByText(threshold.toFixed(4), { exact: true })).toBeVisible();
  await expect(result.getByText("fraud_detector_v1")).toBeVisible();
  await expect(result.getByText("New", { exact: true })).toBeVisible();
  await expect(result.locator("dd.score")).not.toContainText("%");
  await expect(page.getByRole("heading", { name: "Explanation" })).toBeVisible();
  await expectNoProbabilityClaims(page);
  expect(problems.list).toEqual([]);
});

test("presents an unflagged score without opening an investigation", async ({ page }) => {
  await page.goto("/analyse");
  const stored = await scoreThroughForm(page, { amount: UNFLAGGED_INPUT.amount, type: "TRANSFER", step: "400", id: uniqueId("E2E-LOW") });
  expect(stored.prediction).toBe("NOT_FLAGGED");
  const result = page.getByRole("article", { name: "Prediction result" });
  await expect(result.getByText("Not flagged")).toBeVisible();
  await expect(result.getByText("None opened")).toBeVisible();
  await expect(result.locator("dd.score")).toHaveText(stored.model_score.toFixed(4));
});

test("discloses the measured limitations exactly as saved", async ({ page }) => {
  const metrics = JSON.parse(repoFile("artifacts/metadata/model_v1_metrics.json"));
  const test = metrics.test.at_frozen_threshold;
  const target = metrics.threshold.operational_fpr_cap;
  const fpr = `${(test.false_positive_rate * 100).toFixed(3)}%`;
  const multiple = (test.false_positive_rate / target).toFixed(1);
  const recall = `${(test.recall * 100).toFixed(1)}%`;
  const missed = `${(test.false_negative_rate * 100).toFixed(1)}%`;

  await page.goto("/dashboard");
  const disclosure = page.getByRole("complementary", { name: "How to read model scores" });
  await expect(disclosure).toContainText("They are not calibrated and are not the chance that a transaction is fraud.");
  await expect(disclosure).toContainText(`The false positive rate on the test partition was ${fpr}, which is ${multiple} times the`);
  await expect(disclosure).toContainText("The target was not met on test.");
  await expect(disclosure).toContainText(`Overall recall on test was ${recall}, so ${missed} of labelled fraud was not flagged.`);

  // The first three served notes (false positive rate, recall, recall by regime) appear beside
  // scores on the dashboard and scoring pages; every note appears on Model Performance.
  const served = (await (await apiCall(page, "GET", "/api/v1/models/metrics")).json()) as { performance_notes: string[] };
  expect(served.performance_notes.length).toBeGreaterThan(3);
  for (const path of ["/dashboard", "/analyse", "/batches"]) {
    await page.goto(path);
    const compact = page.getByRole("complementary", { name: "How to read model scores" });
    for (const note of served.performance_notes.slice(0, 3)) await expect(compact.getByText(note, { exact: true })).toBeVisible();
    await expectNoProbabilityClaims(page);
  }
  await page.goto("/models");
  const full = page.getByRole("complementary", { name: "How to read model scores" });
  for (const note of served.performance_notes) await expect(full.getByText(note, { exact: true })).toBeVisible();
  await expectNoProbabilityClaims(page);
});

test("stores the prediction and shows it in the explorer", async ({ page }) => {
  await page.goto("/analyse");
  const id = uniqueId("E2E-STORED");
  const stored = await scoreThroughForm(page, { amount: "250000.00", type: "TRANSFER", step: "3", id });

  await page.getByRole("link", { name: "Transaction Explorer" }).click();
  await page.getByLabel("Transaction identifier contains").fill(id);
  await page.getByRole("button", { name: "Apply filters" }).click();
  const table = page.getByRole("table", { name: /transactions/i });
  const row = table.getByRole("row", { name: new RegExp(id) });
  await expect(row).toBeVisible();
  await expect(row).toContainText(stored.model_score.toFixed(4));
  await expect(page.getByText(/1–1 of 1/)).toBeVisible();

  await row.getByRole("button", { name: "Open" }).click();
  const detail = page.getByRole("region", { name: "Transaction detail" });
  await expect(detail.getByRole("heading", { name: `Transaction ${id}` })).toBeVisible();
  await expect(detail).toContainText(stored.model_score.toFixed(4));
});
