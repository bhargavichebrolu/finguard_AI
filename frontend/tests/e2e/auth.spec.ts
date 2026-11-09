/**
 * Sign-in, sign-out, session persistence, expiry and rejection, cookie flags, CSRF, origin
 * checks and CORS, all against the real API.
 */
import { expect, test } from "@playwright/test";

import {
  API_URL,
  BASE_URL,
  NO_SESSION,
  account,
  apiCall,
  changeHeaders,
  runDatabaseScript,
  signInThroughForm,
  startSession,
  statePath,
  uniqueId,
  watchForProblems,
  UNFLAGGED_INPUT,
} from "./support";

test.describe("signing in and out", () => {
  test.use({ storageState: NO_SESSION });

  test("signs in, survives a reload, keeps tokens out of storage, and signs out", async ({ page, context, browserName }) => {
    const problems = await watchForProblems(page, true);
    const signedIn = page.waitForResponse((r) => r.url().endsWith("/api/v1/auth/session") && r.request().method() === "POST");
    await signInThroughForm(page, "logout");
    // What the server sends, whatever the browser does with it: HttpOnly and SameSite=Strict.
    const setCookies = await (await signedIn).headerValues("set-cookie");
    const sessionHeader = setCookies.find((line) => line.startsWith("finguard_session="));
    expect(sessionHeader).toMatch(/HttpOnly/i);
    expect(sessionHeader).toMatch(/SameSite=strict/i);
    await expect(page.getByRole("heading", { name: "Dashboard", level: 1 })).toBeVisible();
    await expect(page.getByText(account("logout").email)).toBeVisible();

    // The session cookie is scoped to /api, so it is read for that path.
    const cookies = await context.cookies(`${BASE_URL}/api/v1/auth/me`);
    const session = cookies.find((cookie) => cookie.name === "finguard_session");
    const csrf = cookies.find((cookie) => cookie.name === "finguard_csrf");
    expect(session, "session cookie").toBeDefined();
    expect(csrf, "CSRF cookie").toBeDefined();
    // HttpOnly and SameSite=Strict always. Secure is off only because this test API runs over
    // plain HTTP with APP_ENV=test; production refuses to start without it (test_config.py).
    expect(session).toMatchObject({ httpOnly: true, secure: false, path: "/api" });
    expect(csrf).toMatchObject({ httpOnly: false, path: "/" });
    // Playwright's WebKit build on Windows reports SameSite as None for these cookies although the
    // server sends Strict (checked above); CSRF tokens and origin checks protect changes anyway.
    if (browserName !== "webkit") {
      expect(session?.sameSite).toBe("Strict");
      expect(csrf?.sameSite).toBe("Strict");
    }
    expect(await page.evaluate(() => document.cookie)).not.toContain("finguard_session");

    const stored = await page.evaluate(() => JSON.stringify({ ...localStorage, ...sessionStorage }));
    expect(stored).not.toContain(session!.value);
    expect(stored).not.toContain(csrf!.value);
    expect(stored).toBe("{}");

    await page.reload();
    await expect(page.getByRole("heading", { name: "Dashboard", level: 1 })).toBeVisible();

    await page.getByRole("button", { name: "Sign out" }).click();
    await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
    await expect(page.getByRole("status")).toHaveText("You have signed out.");
    expect((await apiCall(page, "GET", "/api/v1/auth/me")).status()).toBe(401);

    // The old cookie is revoked on the server, so replaying it does not help.
    await context.addCookies([session!]);
    expect((await apiCall(page, "GET", "/api/v1/auth/me")).status()).toBe(401);
    expect(problems.list).toEqual([]);
  });

  test("gives one message for a wrong password and an unknown account", async ({ page }) => {
    await page.goto("/login");
    for (const email of [account("analyst").email, "nobody@e2e.example.com"]) {
      await page.getByLabel("Email").fill(email);
      await page.getByLabel("Password").fill("not-the-right-password");
      await page.getByRole("button", { name: "Sign in" }).click();
      await expect(page.getByRole("alert")).toHaveText("Incorrect email or password.");
    }
  });

  test("limits repeated failed sign-ins", async ({ page, browser }) => {
    // The limit is kept in the API's memory for a minute, so each run uses a new account,
    // created by an administrator through the API.
    const email = `lockout-${uniqueId("u").toLowerCase()}@e2e.example.com`;
    const password = `Pw-${uniqueId("x")}-${uniqueId("y")}`;
    const admin = await browser.newContext({ storageState: statePath("admin") });
    const adminPage = await admin.newPage();
    expect((await apiCall(adminPage, "POST", "/api/v1/users", { email, password, role: "analyst" })).status()).toBe(201);
    await admin.close();

    for (let attempt = 0; attempt < 5; attempt += 1) {
      expect((await startSession(page, email, "wrong-password-attempt")).status()).toBe(401);
    }
    // Even the right password is refused while the limit holds.
    const limited = await startSession(page, email, password);
    expect(limited.status()).toBe(429);
    expect(Number(limited.headers()["retry-after"])).toBeGreaterThan(0);

    await page.goto("/login");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill("wrong-password-attempt");
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page.getByRole("alert")).toContainText(/Too many attempts\. Try again in \d+ seconds\./);
  });

  test("ends a session that has expired on the server", async ({ page }) => {
    await signInThroughForm(page, "expiry");
    runDatabaseScript("expire-sessions", account("expiry").email);
    await page.getByRole("link", { name: "Transaction Explorer" }).click();
    await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
    await expect(page.getByRole("status")).toHaveText("Your session has ended. Please sign in again.");
    expect((await apiCall(page, "GET", "/api/v1/auth/me")).status()).toBe(401);
  });

  test("rejects a tampered session cookie", async ({ page, context }) => {
    await context.addCookies([
      { name: "finguard_session", value: "not-a-real-token", domain: "127.0.0.1", path: "/api", httpOnly: true, sameSite: "Strict" },
    ]);
    await page.goto("/dashboard");
    await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
    await expect(page).toHaveURL(/\/login$/);
  });

  test("refuses sign-in from another origin", async ({ page }) => {
    const { email, password } = account("analyst");
    const response = await page.request.post(`${BASE_URL}/api/v1/auth/session`, {
      data: { email, password },
      headers: { Origin: "http://evil.example" },
    });
    expect(response.status()).toBe(403);
  });
});

test.describe("protection of changing requests", () => {
  test.use({ storageState: statePath("analyst") });

  test("needs the CSRF token and an allowed origin, but reads need neither", async ({ page }) => {
    await page.goto("/dashboard");
    const url = `${BASE_URL}/api/v1/transactions/predict`;
    const good = await changeHeaders(page.context());

    const missing = await page.request.post(url, { data: UNFLAGGED_INPUT, headers: { Origin: BASE_URL } });
    expect(missing.status()).toBe(403);
    expect((await missing.json()).detail).toBe("The CSRF token is missing or does not match.");

    const wrong = await page.request.post(url, { data: UNFLAGGED_INPUT, headers: { ...good, "X-CSRF-Token": "forged" } });
    expect(wrong.status()).toBe(403);

    const foreign = await page.request.post(url, { data: UNFLAGGED_INPUT, headers: { ...good, Origin: "http://evil.example" } });
    expect(foreign.status()).toBe(403);
    expect((await foreign.json()).detail).toBe("This request did not come from an allowed origin.");

    const noOrigin = await page.request.post(url, { data: UNFLAGGED_INPUT, headers: { "X-CSRF-Token": good["X-CSRF-Token"] } });
    expect(noOrigin.status()).toBe(403);

    expect((await page.request.post(url, { data: UNFLAGGED_INPUT, headers: good })).status()).toBe(201);
    expect((await page.request.get(`${BASE_URL}/api/v1/auth/me`)).status()).toBe(200);
  });

  test("sends security headers on API responses and on the page", async ({ page }) => {
    const pageResponse = await page.goto("/dashboard");
    expect(pageResponse?.headers()["content-security-policy"]).toContain("default-src 'self'");
    expect(pageResponse?.headers()["content-security-policy"]).toContain("frame-ancestors 'none'");
    const api = await page.request.get(`${BASE_URL}/api/v1/auth/me`);
    expect(api.headers()["content-security-policy"]).toBe("default-src 'none'; frame-ancestors 'none'");
    expect(api.headers()["x-content-type-options"]).toBe("nosniff");
  });
});

test.describe("cross-origin requests", () => {
  test("CORS answers only the configured origin", async ({ request }) => {
    const preflight = (origin: string) =>
      request.fetch(`${API_URL}/api/v1/transactions/predict`, {
        method: "OPTIONS",
        headers: { Origin: origin, "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type,x-csrf-token" },
      });
    const foreign = await preflight("http://evil.example");
    expect(foreign.headers()["access-control-allow-origin"]).toBeUndefined();

    const allowed = await preflight(BASE_URL);
    expect(allowed.headers()["access-control-allow-origin"]).toBe(BASE_URL);
    expect(allowed.headers()["access-control-allow-credentials"]).toBe("true");

    const read = await request.get(`${API_URL}/health`, { headers: { Origin: "http://evil.example" } });
    expect(read.headers()["access-control-allow-origin"]).toBeUndefined();
  });
});
