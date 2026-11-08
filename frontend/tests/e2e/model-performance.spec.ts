/**
 * Model Performance shows the saved Phase 2 results unchanged. Values on the page are compared
 * with the original saved files (not only the derived report), and each file's hash is checked
 * against the one the report records. Nothing under data/ is read, and the page only reads.
 */
import { createHash } from "node:crypto";

import { expect, test, type Page } from "@playwright/test";

import { repoBytes, repoFile, statePath, watchForProblems } from "./support";

test.use({ storageState: statePath("analyst") });

const FAMILY_NAMES: Record<string, string> = {
  logistic_regression: "Logistic Regression",
  decision_tree: "Decision Tree",
  random_forest: "Random Forest",
  xgboost: "XGBoost",
  lightgbm: "LightGBM",
  catboost: "CatBoost",
};
const count = (value: number) => new Intl.NumberFormat("en-GB").format(value);
const rate = (value: number, digits = 1) => `${(value * 100).toFixed(digits)}%`;

const report = JSON.parse(repoFile("artifacts/metadata/model_v1_report.json"));
const selection = JSON.parse(repoFile("experiments/results/phase2/selection.json"));
const testEvaluation = JSON.parse(repoFile("experiments/results/phase2/test_evaluation.json"));
const metrics = JSON.parse(repoFile("artifacts/metadata/model_v1_metrics.json"));
const metadata = JSON.parse(repoFile("artifacts/metadata/model_v1.json"));
const runs = repoFile("experiments/results/phase2/all_runs.csv").trim().split(/\r?\n/).slice(1);
const runIds = runs.map((line) => line.split(",")[0]);
const runStages = runs.map((line) => line.split(",")[1]);

async function openPage(page: Page) {
  await page.goto("/models");
  await expect(page.getByRole("heading", { name: "Model Performance", level: 1 })).toBeVisible();
  await expect(page.getByRole("table", { name: "Model comparison on validation" })).toBeVisible();
}

test("every saved source file still matches the hash the report records", () => {
  for (const [file, hash] of Object.entries(report.source_files as Record<string, string>)) {
    expect(file.startsWith("data/")).toBe(false);
    expect(createHash("sha256").update(repoBytes(file)).digest("hex"), file).toBe(hash);
  }
});

test("shows each family's validation results as saved in selection.json", async ({ page }) => {
  const problems = await watchForProblems(page);
  await openPage(page);
  const table = page.getByRole("table", { name: "Model comparison on validation" });
  const candidates = selection.candidates as { family: string; pr_auc: number; roc_auc: number; at_fpr_cap: Record<string, number> }[];
  expect(candidates).toHaveLength(6);
  for (const candidate of candidates) {
    const row = table.getByRole("row", { name: new RegExp(`^${FAMILY_NAMES[candidate.family]}`) });
    const interval = selection.pr_auc_intervals[candidate.family];
    await expect(row).toContainText(candidate.pr_auc.toFixed(4));
    await expect(row).toContainText(`${interval.ci_low.toFixed(3)}–${interval.ci_high.toFixed(3)}`);
    await expect(row).toContainText(candidate.roc_auc.toFixed(4));
    await expect(row).toContainText(rate(candidate.at_fpr_cap.precision));
    await expect(row).toContainText(rate(candidate.at_fpr_cap.recall));
    await expect(row).toContainText(rate(candidate.at_fpr_cap.false_positive_rate, 3));
  }
  const decision = selection.decision;
  await expect(table.getByRole("row", { name: new RegExp(`^${FAMILY_NAMES[decision.selected_family]}`) })).toContainText("Selected");
  for (const family of decision.statistically_indistinguishable.filter((name: string) => name !== decision.selected_family)) {
    await expect(table.getByRole("row", { name: new RegExp(`^${FAMILY_NAMES[family]}`) })).toContainText("Tied");
  }
  for (const note of report.notes as string[]) await expect(page.getByText(note, { exact: true })).toBeVisible();
  expect(problems.list).toEqual([]);
});

test("keeps validation and test apart, with test counts from test_evaluation.json", async ({ page }) => {
  await openPage(page);
  const frozen = testEvaluation.overall.at_frozen_threshold;
  const testTable = page.getByRole("table", { name: "Test, evaluated once" });
  await expect(testTable.getByRole("row", { name: /Labelled fraud/ })).toContainText(`${count(frozen.true_positives)}${count(frozen.false_negatives)}`);
  await expect(testTable.getByRole("row", { name: /Labelled legitimate/ })).toContainText(`${count(frozen.false_positives)}${count(frozen.true_negatives)}`);

  const validation = metrics.validation.at_threshold;
  const validationTable = page.getByRole("table", { name: "Validation", exact: true });
  await expect(validationTable.getByRole("row", { name: /Labelled fraud/ })).toContainText(`${count(validation.true_positives)}${count(validation.false_negatives)}`);
  await expect(validationTable.getByRole("row", { name: /Labelled legitimate/ })).toContainText(`${count(validation.false_positives)}${count(validation.true_negatives)}`);

  for (const regime of ["normal", "sparse"]) {
    const saved = testEvaluation.regimes[regime].at_frozen_threshold;
    const table = page.getByRole("table", { name: `Test, ${regime} steps` });
    await expect(table.getByRole("row", { name: /Labelled fraud/ })).toContainText(`${count(saved.true_positives)}${count(saved.false_negatives)}`);
  }
  await expect(page.getByRole("heading", { name: "Model comparison on validation" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Threshold comparison (validation)" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Imbalance strategies: PR-AUC on validation" })).toBeVisible();

  const thresholds = page.getByRole("table", { name: "Thresholds compared on validation" });
  await expect(thresholds.getByRole("row", { name: /^Frozen threshold/ })).toContainText(metadata.threshold.value.toFixed(4));
  await expect(thresholds.getByRole("row", { name: /^Frozen threshold/ })).toContainText(rate(validation.recall));
});

test("draws both curves per chart and offers their data as a table", async ({ page }) => {
  await openPage(page);
  const card = page.getByRole("article").filter({ has: page.getByRole("heading", { name: "Precision against recall: selected model" }) });
  await expect(card.locator(".recharts-line-curve")).toHaveCount(2);
  for (const path of await card.locator(".recharts-line-curve").all()) {
    expect(((await path.getAttribute("d")) ?? "").length).toBeGreaterThan(100);
  }
  await card.getByRole("button", { name: "Show table" }).click();
  await expect(card.getByRole("button", { name: "Show chart" })).toHaveAttribute("aria-pressed", "true");
  const curves = report.selected_model_curves;
  await expect(card.getByRole("row", { name: /Validation/ })).toContainText(String(curves.validation.pr_recall.length));
  await expect(card.getByRole("row", { name: /Test/ })).toContainText(String(curves.test.pr_recall.length));

  await page.getByLabel("Compare a family with the selected model on validation").selectOption("logistic_regression");
  const compare = page.getByRole("article").filter({ has: page.getByRole("heading", { name: /on validation: Logistic Regression and XGBoost/ }) });
  await expect(compare.locator(".recharts-line-curve")).toHaveCount(2);
});

test("lists every recorded run from all_runs.csv, by stage", async ({ page }) => {
  await openPage(page);
  await expect(page.getByText(`All ${runIds.length} recorded runs, on validation data.`)).toBeVisible();
  const history = page.getByRole("table", { name: "Recorded experiment runs" });
  const pager = page.getByRole("navigation", { name: "Pages" }).last();
  await expect(pager).toContainText(`1–25 of ${runIds.length}`);
  const shown = await history.locator("tbody tr td:first-child").allInnerTexts();
  expect(shown).toHaveLength(25);
  for (const id of shown) expect(runIds).toContain(id.trim());

  const tuning = runStages.filter((stage) => stage === "tuning").length;
  await page.getByLabel("Stage").selectOption("tuning");
  await expect(pager).toContainText(`of ${tuning}`);
  for (const stage of await history.locator("tbody tr td:nth-child(2)").allInnerTexts()) expect(stage).toBe("Tuning");
});

test("only reads: no changes, no retraining, nothing from the dataset folder", async ({ page }) => {
  const requests: string[] = [];
  page.on("request", (request) => {
    if (new URL(request.url()).pathname.startsWith("/api") || request.url().includes("/data/")) requests.push(`${request.method()} ${new URL(request.url()).pathname}`);
  });
  await openPage(page);
  await page.getByLabel("Stage").selectOption("matrix");
  await page.getByLabel("Compare a family with the selected model on validation").selectOption("catboost");
  expect(requests.every((entry) => entry.startsWith("GET "))).toBe(true);
  expect(requests.some((entry) => entry.includes("/data/"))).toBe(false);
  expect(new Set(requests)).toEqual(new Set(["GET /api/v1/auth/me", "GET /api/v1/models/metrics", "GET /api/v1/models/report"]));
});
