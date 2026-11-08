/**
 * CSV batches through the real API: file checks, column refusals, progress, row-level errors,
 * paged results, and downloads that are safe to open in a spreadsheet.
 */
import { readFileSync } from "node:fs";

import { expect, test, type Page } from "@playwright/test";

import { statePath, uniqueId, watchForProblems } from "./support";

test.use({ storageState: statePath("analyst") });

const HEADER = "external_transaction_id,amount,transaction_type,step,destination_category";
const FORMULA_START = /^[=+\-@\t\r]/;

function csvFile(name: string, body: string) {
  return { name, mimeType: "text/csv", buffer: Buffer.from(body, "utf-8") };
}

function goodRows(prefix: string, count: number): string[] {
  const types = ["TRANSFER", "CASH_OUT", "CASH_IN", "DEBIT"];
  return Array.from({ length: count }, (_, index) => {
    const type = types[index % types.length];
    return `${prefix}-${index},${(1000 + index * 137.25).toFixed(2)},${type},${1 + (index % 700)},customer`;
  });
}

/** Split one CSV line, honouring double quotes. */
function cells(line: string): string[] {
  const out: string[] = [];
  let current = "";
  let quoted = false;
  for (let index = 0; index < line.length; index += 1) {
    const character = line[index];
    if (quoted && character === '"' && line[index + 1] === '"') {
      current += '"';
      index += 1;
    } else if (character === '"') {
      quoted = !quoted;
    } else if (character === "," && !quoted) {
      out.push(current);
      current = "";
    } else {
      current += character;
    }
  }
  out.push(current);
  return out;
}

async function download(page: Page, button: string): Promise<{ name: string; lines: string[] }> {
  const pending = page.waitForEvent("download");
  await page.getByRole("button", { name: button }).click();
  const file = await pending;
  const text = readFileSync((await file.path())!, "utf-8");
  return { name: file.suggestedFilename(), lines: text.trim().split(/\r?\n/) };
}

/** No cell may begin a spreadsheet formula, unless it was neutralised with a leading quote. */
function expectSpreadsheetSafe(lines: string[]): void {
  const unsafe = lines.flatMap(cells).filter((cell) => FORMULA_START.test(cell));
  expect(unsafe).toEqual([]);
}

async function upload(page: Page, file: ReturnType<typeof csvFile>): Promise<void> {
  await page.getByLabel("CSV file").setInputFiles(file);
  await page.getByRole("button", { name: "Upload and score" }).click();
}

test("checks the file before uploading", async ({ page }) => {
  await page.goto("/batches");
  await page.getByLabel("CSV file").setInputFiles({ name: "notes.txt", mimeType: "text/plain", buffer: Buffer.from("a,b") });
  await expect(page.getByRole("alert")).toHaveText("Choose a .csv file.");
  await expect(page.getByRole("button", { name: "Upload and score" })).toBeDisabled();

  await page.getByLabel("CSV file").setInputFiles(csvFile("empty.csv", ""));
  await expect(page.getByRole("alert")).toHaveText("The file is empty.");
  await expect(page.getByRole("button", { name: "Upload and score" })).toBeDisabled();
});

test("refuses columns that are not available when a transaction is scored", async ({ page }) => {
  await page.goto("/batches");
  await upload(page, csvFile("balances.csv", `${HEADER},oldbalanceOrg\nX-1,10.00,TRANSFER,1,customer,500\n`));
  await expect(page.getByText(/These columns are not available at prediction time, so they are refused: \['oldbalanceOrg'\]/)).toBeVisible();

  await upload(page, csvFile("missing.csv", "amount,transaction_type\n10.00,TRANSFER\n"));
  await expect(page.getByText(/Missing required columns/)).toBeVisible();
});

test("scores good rows, reports bad rows, pages results and exports safely", async ({ page }) => {
  const problems = await watchForProblems(page, true);
  const prefix = uniqueId("B");
  const good = goodRows(prefix, 60);
  // Three bad rows, two of them shaped like spreadsheet formulas.
  const bad = [`${prefix}-bad-1,-5,TRANSFER,1,customer`, `${prefix}-bad-2,10.00,=1+1,1,customer`, `@SUM(A1),10.00,TRANSFER,1,customer`];
  const body = `${HEADER},isFraud\n${[...good, ...bad].map((row) => `${row},0`).join("\n")}\n`;
  const name = `${prefix.toLowerCase()}.csv`;

  await page.goto("/batches");
  await upload(page, csvFile(name, body));
  const status = page.getByRole("article", { name: "Batch status" });
  await expect(status.getByText("Completed with errors: 63 of 63 rows")).toBeVisible({ timeout: 30_000 });
  await expect(status.locator("#processing-progress")).toHaveAttribute("value", "100");
  await expect(status).toContainText("Scored and stored60");
  await expect(status).toContainText("Refused3");
  await expect(status).toContainText("isFraud: kept out of scoring");
  await expect(status).toContainText("Yes, stored separately and never used to score");
  await expect(page.getByRole("table", { name: "Recent batch uploads" }).getByRole("row", { name: new RegExp(name) })).toBeVisible();

  const results = page.getByRole("table", { name: "Batch results" });
  await expect(page.getByText("1–25 of 60")).toBeVisible();
  const scores = (await results.locator("tbody tr td:nth-child(5)").allInnerTexts()).map(Number);
  expect(scores).toHaveLength(25);
  expect([...scores].sort((a, b) => b - a)).toEqual(scores);
  await page.getByRole("button", { name: "Next page" }).click();
  await expect(page.getByText("26–50 of 60")).toBeVisible();
  await page.getByRole("button", { name: "Next page" }).click();
  await expect(page.getByText("51–60 of 60")).toBeVisible();
  await expect(page.getByRole("button", { name: "Next page" })).toBeDisabled();

  const exported = await download(page, "Download results");
  expect(exported.name).toMatch(/\.csv$/);
  expect(exported.lines[0]).toBe(
    "external_transaction_id,transaction_type,amount,step,destination_category,model_score,score_is_calibrated,risk_score,risk_level,prediction,model_version,threshold_used,high_risk_boundary_used,investigation_status,created_at",
  );
  expect(exported.lines).toHaveLength(61);
  expect(exported.lines.slice(1).every((line) => cells(line)[6] === "False" || cells(line)[6] === "false")).toBe(true);
  expect(exported.lines.join("\n")).not.toMatch(/isFraud|is_fraud/);
  expectSpreadsheetSafe(exported.lines);

  const errors = await download(page, "Download error report");
  expect(errors.lines[0]).toBe("row_number,column,message");
  const rows = errors.lines.slice(1).map(cells);
  expect(rows.map((row) => row[0]).sort()).toEqual(["62", "63", "64"]);
  expect(rows.find((row) => row[0] === "62")?.[1]).toBe("amount");
  expect(rows.find((row) => row[0] === "63")?.[1]).toBe("transaction_type");
  expect(rows.find((row) => row[0] === "64")?.[1]).toBe("external_transaction_id");
  expectSpreadsheetSafe(errors.lines);
  expect(problems.list).toEqual([]);
});

test("shows processing progress for a larger file until it completes", async ({ page }) => {
  const prefix = uniqueId("P");
  const rows = 20_000;
  await page.goto("/batches");
  await upload(page, csvFile(`${prefix.toLowerCase()}.csv`, `${HEADER}\n${goodRows(prefix, rows).join("\n")}\n`));

  const status = page.getByRole("article", { name: "Batch status" });
  const progress = status.locator("#processing-progress");
  await expect(progress).toBeVisible();
  const seen: number[] = [];
  const labels = new Set<string>();
  await expect
    .poll(
      async () => {
        seen.push(Number(await progress.getAttribute("value")));
        labels.add((await status.locator("label[for=processing-progress]").innerText()).split(":")[0]);
        return seen[seen.length - 1];
      },
      { timeout: 120_000, intervals: [250] },
    )
    .toBe(100);
  await expect(status.getByText(`Completed: 20,000 of 20,000 rows`)).toBeVisible();
  // Progress only moves forward, and the page showed the job before it had finished.
  expect([...seen].sort((a, b) => a - b)).toEqual(seen);
  expect(seen[0]).toBeLessThan(100);
  expect(labels.size).toBeGreaterThan(1);
  await expect(page.getByText("1–25 of 20,000")).toBeVisible();
});
