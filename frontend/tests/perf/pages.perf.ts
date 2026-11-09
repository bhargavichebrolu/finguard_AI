/**
 * Times each page from navigation start until its content is usable: the page heading is shown
 * and no loading state remains. Cold runs use a new browser context (empty cache); warm runs
 * reuse one. Every figure comes from this run and is written to a JSON file.
 */
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { expect, test, type Browser, type Page } from "@playwright/test";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = process.env.FINGUARD_PERF_OUT ?? path.resolve(HERE, "../../../docs/performance/phase-5-pages.json");
const ACCOUNTS = path.resolve(HERE, "../../.e2e/accounts.json");
const COLD_RUNS = 3;
const WARM_RUNS = 5;
const PAGES = [
  { path: "/dashboard", heading: "Dashboard" },
  { path: "/analyse", heading: "Transaction Analysis" },
  { path: "/batches", heading: "CSV Batch Analysis" },
  { path: "/transactions", heading: "Transaction Explorer" },
  { path: "/investigations", heading: "Investigation Centre" },
  { path: "/models", heading: "Model Performance" },
  { path: "/explainability", heading: "Explainable AI" },
  { path: "/reports", heading: "Reports" },
  { path: "/settings", heading: "Settings" },
  { path: "/system", heading: "System Information" },
];

interface Sample {
  readyMs: number;
  domContentLoadedMs: number;
  transferredBytes: number;
}

/** Sign in once through the form and return the saved state. The password is never logged. */
async function signedInState(browser: Browser): Promise<string> {
  const { email, password } = JSON.parse(readFileSync(ACCOUNTS, "utf-8")).admin as { email: string; password: string };
  const context = await browser.newContext();
  const page = await context.newPage();
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("button", { name: "Sign out" })).toBeVisible();
  const state = path.resolve(HERE, "../../.e2e/state-perf.json");
  await context.storageState({ path: state });
  await context.close();
  return state;
}

async function measure(page: Page, target: { path: string; heading: string }): Promise<Sample> {
  await page.goto(target.path);
  await expect(page.getByRole("heading", { name: target.heading, level: 1 })).toBeVisible({ timeout: 120_000 });
  await expect(page.locator(".state[role='status']")).toHaveCount(0, { timeout: 120_000 });
  return page.evaluate(() => {
    const navigation = performance.getEntriesByType("navigation")[0] as PerformanceNavigationTiming;
    const resources = performance.getEntriesByType("resource") as PerformanceResourceTiming[];
    return {
      readyMs: Math.round(performance.now()),
      domContentLoadedMs: Math.round(navigation.domContentLoadedEventEnd),
      transferredBytes: navigation.transferSize + resources.reduce((sum, entry) => sum + entry.transferSize, 0),
    };
  });
}

function median(values: number[]): number {
  const ordered = [...values].sort((a, b) => a - b);
  const middle = Math.floor(ordered.length / 2);
  return ordered.length % 2 ? ordered[middle] : Math.round((ordered[middle - 1] + ordered[middle]) / 2);
}

test("time every page, cold and warm", async ({ browser }) => {
  const state = await signedInState(browser);
  const results: Record<string, unknown> = {};
  for (const target of PAGES) {
    const cold: Sample[] = [];
    for (let run = 0; run < COLD_RUNS; run += 1) {
      const context = await browser.newContext({ storageState: state });
      cold.push(await measure(await context.newPage(), target));
      await context.close();
    }
    const context = await browser.newContext({ storageState: state });
    const page = await context.newPage();
    await measure(page, target); // fills the cache, not recorded
    const warm: Sample[] = [];
    for (let run = 0; run < WARM_RUNS; run += 1) warm.push(await measure(page, target));
    await context.close();
    results[target.path] = {
      cold_ready_ms_median: median(cold.map((s) => s.readyMs)),
      cold_ready_ms_max: Math.max(...cold.map((s) => s.readyMs)),
      cold_transferred_bytes_median: median(cold.map((s) => s.transferredBytes)),
      warm_ready_ms_median: median(warm.map((s) => s.readyMs)),
      warm_ready_ms_max: Math.max(...warm.map((s) => s.readyMs)),
      dom_content_loaded_ms_median: median(cold.map((s) => s.domContentLoadedMs)),
      runs: { cold: COLD_RUNS, warm: WARM_RUNS },
    };
  }
  mkdirSync(path.dirname(OUT), { recursive: true });
  writeFileSync(OUT, `${JSON.stringify({ measured_at: new Date().toISOString(), viewport: "1440x900", browser: "Chromium (Playwright)", pages: results }, null, 2)}\n`);
});
