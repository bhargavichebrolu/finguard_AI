/**
 * Shared helpers for the browser tests: test accounts, saved sessions, calls to the real API
 * with the CSRF header, the test-database script, and a watcher for browser-side problems.
 */
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { expect, type APIResponse, type Browser, type BrowserContext, type Page } from "@playwright/test";

export const FRONTEND_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
export const REPO_ROOT = path.resolve(FRONTEND_DIR, "..");
export const STATE_DIR = path.join(FRONTEND_DIR, ".e2e");
export const SCREENSHOT_DIR = path.join(STATE_DIR, "screenshots");
export const ACCOUNTS_FILE = path.join(STATE_DIR, "accounts.json");
export const BASE_URL = "http://127.0.0.1:4173";
export const API_URL = process.env.FINGUARD_E2E_API ?? "http://127.0.0.1:8011";
export const NO_SESSION = { cookies: [], origins: [] };

export type AccountName =
  | "admin"
  | "investigator"
  | "analyst"
  | "demo"
  | "colleague"
  | "logout"
  | "expiry"
  | "password"
  | "deactivate";

export interface Account {
  email: string;
  password: string;
  role: string;
}

/** A seeded account. Passwords are read from the Git-ignored file and never logged. */
export function account(name: AccountName): Account {
  const accounts = JSON.parse(readFileSync(ACCOUNTS_FILE, "utf-8")) as Record<AccountName, Account>;
  return accounts[name];
}

/** Where a role's signed-in browser state is saved by the setup project. */
export function statePath(name: AccountName): string {
  return path.join(STATE_DIR, `state-${name}.json`);
}

/** Read a file from the repository as bytes. The dataset folder is refused. */
export function repoBytes(relative: string): Buffer {
  if (relative.startsWith("data/") || relative.startsWith("data\\")) {
    throw new Error("Browser tests never read the dataset folder.");
  }
  return readFileSync(path.join(REPO_ROOT, relative));
}

/** Read a file from the repository as text, for comparing the interface with saved results. */
export function repoFile(relative: string): string {
  return repoBytes(relative).toString("utf-8");
}

function pythonPath(): string {
  if (process.env.FINGUARD_PYTHON) return process.env.FINGUARD_PYTHON;
  const venv = path.join(REPO_ROOT, "backend", ".venv");
  return process.platform === "win32" ? path.join(venv, "Scripts", "python.exe") : path.join(venv, "bin", "python");
}

/** Run scripts/e2e_database.py, which refuses any database not named *_test. */
export function runDatabaseScript(...args: string[]): string {
  return execFileSync(pythonPath(), ["-I", path.join(REPO_ROOT, "scripts", "e2e_database.py"), ...args], {
    cwd: REPO_ROOT,
    encoding: "utf-8",
  });
}

/**
 * Restart the browser-test API container gracefully (SIGTERM, then start), as a deploy would.
 * Needs the Docker CLI on PATH. The container keeps its environment, so sessions stay valid.
 */
export function restartApiContainer(): void {
  execFileSync("docker", ["restart", "--time", "30", API_CONTAINER], { stdio: "ignore" });
}

const API_CONTAINER = process.env.FINGUARD_E2E_CONTAINER ?? "finguard-api-e2e-1";

/** Stop the browser-test API, as a crash or a deploy in progress would leave it (Phase 5 M7). */
export function stopApiContainer(): void {
  execFileSync("docker", ["stop", "--time", "30", API_CONTAINER], { stdio: "ignore" });
}

/** Start the browser-test API again and wait until it answers. */
export async function startApiContainer(): Promise<void> {
  execFileSync("docker", ["start", API_CONTAINER], { stdio: "ignore" });
  await waitForApi();
}

/** Wait until the browser-test API answers its health check. */
export async function waitForApi(): Promise<void> {
  await expect
    .poll(
      async () => {
        try {
          return (await fetch(`${API_URL}/health`)).status;
        } catch {
          return 0;
        }
      },
      { timeout: 120_000, intervals: [500] },
    )
    .toBe(200);
}

/**
 * Simulate an outage of the browser-test database only: new connections are refused and open
 * ones ended, as when a database server restarts (Phase 5 M7). Other databases are untouched.
 * Always pair with setDatabaseAvailable(true) in a finally block; `e2e_stack.py up` also ends
 * any outage a stopped run left behind.
 */
export function setDatabaseAvailable(available: boolean): void {
  execFileSync(pythonPath(), ["-I", path.join(REPO_ROOT, "scripts", "e2e_stack.py"), "database", available ? "on" : "off"], {
    cwd: REPO_ROOT,
    stdio: "ignore",
  });
}

/** Headers a changing request needs from a signed-in browser: its CSRF token and origin. */
export async function changeHeaders(context: BrowserContext, origin = BASE_URL): Promise<Record<string, string>> {
  // Prefixed __Host- when cookies are Secure, as on the HTTPS production-like stack.
  const names = ["__Host-finguard_csrf", "finguard_csrf"];
  const csrf = (await context.cookies()).find((cookie) => names.includes(cookie.name));
  return { "X-CSRF-Token": csrf?.value ?? "", Origin: origin };
}

/** Call the API with the page's session, as the interface would. */
export async function apiCall(
  page: Page,
  method: "GET" | "POST" | "PATCH" | "DELETE",
  url: string,
  data?: unknown,
): Promise<APIResponse> {
  const headers = method === "GET" ? {} : await changeHeaders(page.context());
  return page.request.fetch(`${BASE_URL}${url}`, { method, data, headers });
}

/** Sign in through the form. The password is typed but never printed. */
export async function signInThroughForm(page: Page, name: AccountName, password?: string): Promise<void> {
  const { email, password: seeded } = account(name);
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password ?? seeded);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("button", { name: "Sign out" })).toBeVisible();
}

/** Sign in through the form with given credentials. */
export async function signInWith(page: Page, email: string, password: string): Promise<void> {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("button", { name: "Sign out" })).toBeVisible();
}

/**
 * Create a fresh account through the administrator API. Tests that use an account up, such as
 * changing its password or deactivating it, use one of these so every browser project gets its
 * own (Phase 5 M6: the seeded account was used up by the first browser).
 */
export async function createAccount(browser: Browser, role = "analyst"): Promise<Account> {
  const email = `fresh-${uniqueId("u").toLowerCase()}@e2e.example.com`;
  const password = `Pw-${uniqueId("x")}-${uniqueId("y")}`;
  const context = await browser.newContext({ storageState: statePath("admin") });
  const page = await context.newPage();
  const response = await apiCall(page, "POST", "/api/v1/users", { email, password, role });
  expect(response.status(), "account created").toBe(201);
  await context.close();
  return { email, password, role };
}

/** Start a session through the API, returning the response. */
export async function startSession(page: Page, email: string, password: string): Promise<APIResponse> {
  return page.request.post(`${BASE_URL}/api/v1/auth/session`, {
    data: { email, password },
    headers: { Origin: BASE_URL },
  });
}

export interface Problems {
  list: string[];
}

/**
 * Collect Content Security Policy violations, uncaught errors and console errors. Failed
 * responses that a test provokes on purpose appear as "Failed to load resource"; pass
 * allowFailedRequests for those tests.
 */
export async function watchForProblems(page: Page, allowFailedRequests = false): Promise<Problems> {
  const problems: Problems = { list: [] };
  await page.addInitScript(() => {
    document.addEventListener("securitypolicyviolation", (event) => {
      console.error(`CSP violation: ${event.violatedDirective} ${event.blockedURI}`);
    });
  });
  page.on("pageerror", (error) => problems.list.push(`page error: ${error.message}`));
  page.on("console", (message) => {
    if (message.type() !== "error") return;
    const text = message.text();
    if (allowFailedRequests && text.startsWith("Failed to load resource")) return;
    problems.list.push(`console: ${text}`);
  });
  return problems;
}

/** A unique, valid transaction identifier for this run. */
export function uniqueId(prefix: string): string {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`.toUpperCase();
}

export interface StoredPrediction {
  transaction_id: string;
  external_transaction_id: string;
  model_score: number;
  prediction: string;
  risk_level: string;
  threshold_used: number;
  high_risk_boundary_used: number;
  investigation_id: string | null;
  investigation_status: string | null;
  is_demo: boolean;
}

/** Score one transaction through the API with the page's session. */
export async function predictThroughApi(
  page: Page,
  input: Record<string, unknown>,
  externalId = uniqueId("E2E"),
): Promise<StoredPrediction> {
  const response = await apiCall(page, "POST", "/api/v1/transactions/predict", { ...input, external_transaction_id: externalId });
  expect(response.status(), "prediction stored").toBe(201);
  return (await response.json()) as StoredPrediction;
}

/** Inputs the frozen model flags (HIGH) and does not flag, found by scoring through the API. */
export const FLAGGED_INPUT = { amount: "5000000.00", transaction_type: "CASH_OUT", step: 50, destination_category: "customer" };
export const UNFLAGGED_INPUT = { amount: "1000000.00", transaction_type: "TRANSFER", step: 400, destination_category: "customer" };
