/**
 * Browser tests against the real API and PostgreSQL, never a mock.
 *
 * Before running: `python scripts/e2e_stack.py up` starts the API on 127.0.0.1:8011 against the
 * finguard_test database. Global setup reseeds that database; the web server below builds the
 * app and serves it with the production Content Security Policy, forwarding /api to that API.
 *
 * Credentials: tests type generated passwords, so traces and the HTML report, which record typed
 * values, are switched off. The list reporter prints test titles only.
 */
import { defineConfig, devices } from "@playwright/test";

const API_URL = process.env.FINGUARD_E2E_API ?? "http://127.0.0.1:8011";
export const BASE_URL = "http://127.0.0.1:4173";

const desktop = { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } };
const tablet = { ...devices["Desktop Chrome"], viewport: { width: 768, height: 1024 }, hasTouch: true };
// Phase 5 M6: the same tests in Firefox and WebKit (Playwright's builds). WebKit here is the
// engine Safari uses, run on this machine; it is not Safari on macOS or iOS.
const firefox = { ...devices["Desktop Firefox"], viewport: { width: 1440, height: 900 } };
const webkit = { ...devices["Desktop Safari"], viewport: { width: 1440, height: 900 } };
const webkitMobile = {
  ...devices["Desktop Safari"],
  viewport: { width: 390, height: 844 },
  hasTouch: true,
};
const mobile = {
  ...devices["Desktop Chrome"],
  viewport: { width: 390, height: 844 },
  isMobile: true,
  hasTouch: true,
  deviceScaleFactor: 3,
};

export default defineConfig({
  testDir: "tests/e2e",
  outputDir: "test-results",
  globalSetup: "./tests/e2e/global-setup.ts",
  // One worker: the tests share one database, and some change settings other tests read.
  workers: 1,
  fullyParallel: false,
  retries: 0,
  forbidOnly: true,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  reporter: [["list"]],
  use: {
    baseURL: BASE_URL,
    trace: "off",
    screenshot: "only-on-failure",
    video: "off",
  },
  webServer: {
    command: "npm run build && npx vite preview --port 4173 --strictPort",
    url: `${BASE_URL}/login`,
    env: { FINGUARD_API_PROXY_TARGET: API_URL },
    reuseExistingServer: false,
    timeout: 180_000,
  },
  projects: [
    { name: "setup", testMatch: /sessions\.setup\.ts/, use: desktop },
    { name: "desktop", testMatch: /\.spec\.ts$/, dependencies: ["setup"], use: desktop },
    { name: "tablet", testMatch: /responsive\.spec\.ts$/, dependencies: ["setup"], use: tablet },
    { name: "mobile", testMatch: /responsive\.spec\.ts$/, dependencies: ["setup"], use: mobile },
    { name: "firefox", testMatch: /\.spec\.ts$/, dependencies: ["setup"], use: firefox },
    { name: "webkit", testMatch: /\.spec\.ts$/, dependencies: ["setup"], use: webkit },
    { name: "webkit-mobile", testMatch: /responsive\.spec\.ts$/, dependencies: ["setup"], use: webkitMobile },
  ],
});
