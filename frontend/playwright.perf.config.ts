/**
 * Page timing measurements (Phase 5 M2), separate from the browser tests.
 *
 * No global setup: this must not reseed the database, because it measures pages against the
 * volume loaded by scripts/measure_performance.py. Run it after that script, with the same
 * browser-test API running. Results go to FINGUARD_PERF_OUT (default
 * ../docs/performance/phase-5-pages.json).
 */
import { defineConfig, devices } from "@playwright/test";

const API_URL = process.env.FINGUARD_E2E_API ?? "http://127.0.0.1:8011";

export default defineConfig({
  testDir: "tests/perf",
  testMatch: /\.perf\.ts$/,
  outputDir: "test-results/perf",
  workers: 1,
  retries: 0,
  timeout: 600_000,
  reporter: [["list"]],
  use: {
    baseURL: "http://127.0.0.1:4173",
    ...devices["Desktop Chrome"],
    viewport: { width: 1440, height: 900 },
    trace: "off",
    video: "off",
  },
  webServer: {
    command: "npm run build && npx vite preview --port 4173 --strictPort",
    url: "http://127.0.0.1:4173/login",
    env: { FINGUARD_API_PROXY_TARGET: API_URL },
    reuseExistingServer: false,
    timeout: 180_000,
  },
});
