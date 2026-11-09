/**
 * Browser tests against the production-like stack (Phase 5 M5): HTTPS through Caddy, one origin,
 * APP_ENV=production. Start it first with `python scripts/prodlike_stack.py up`.
 *
 * The certificate comes from Caddy's local authority, which the test browser does not trust, so
 * certificate errors are ignored; everything else (Secure and prefixed cookies, HSTS, CSRF,
 * origin checks, proxy headers) behaves as in production.
 */
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "tests/prodlike",
  testMatch: /\.spec\.ts$/,
  outputDir: "test-results/prodlike",
  globalSetup: "./tests/prodlike/global-setup.ts",
  workers: 1,
  retries: 0,
  forbidOnly: true,
  timeout: 60_000,
  reporter: [["list"]],
  use: {
    ...devices["Desktop Chrome"],
    baseURL: "https://127.0.0.1:8443",
    ignoreHTTPSErrors: true,
    viewport: { width: 1440, height: 900 },
    trace: "off",
    video: "off",
    screenshot: "only-on-failure",
  },
});
