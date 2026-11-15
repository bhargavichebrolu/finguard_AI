/**
 * The complete HTTPS path through Caddy with production settings (Phase 5 M5): redirects,
 * Secure prefixed cookies, HSTS and CSP, CSRF and origin checks, CORS, forwarded-header trust.
 */
import { execFileSync } from "node:child_process";

import { expect, test, type Page } from "@playwright/test";

import { CONTENT_SECURITY_POLICY } from "../../vite.config";
import { watchForProblems } from "../e2e/support";
import { CADDY_ADDRESS, DIRECT_API, PLAIN_HTTP, SITE, prodlikeAccount } from "./prodlike";

const PREDICT = `${SITE}/api/v1/transactions/predict`;
const INPUT = { amount: "1000000.00", transaction_type: "TRANSFER", step: 400, destination_category: "customer" };

async function signIn(page: Page, name = "analyst"): Promise<void> {
  const { email, password } = prodlikeAccount(name);
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("button", { name: "Sign out" })).toBeVisible();
}

async function csrfToken(page: Page): Promise<string> {
  const cookie = (await page.context().cookies(SITE)).find((c) => c.name === "__Host-finguard_csrf");
  return cookie?.value ?? "";
}

test("plain HTTP is redirected to HTTPS", async ({ request }) => {
  const response = await request.get(`${PLAIN_HTTP}/dashboard?x=1`, { maxRedirects: 0 });
  expect(response.status()).toBe(308);
  expect(response.headers().location).toBe(`${SITE}/dashboard?x=1`);
});

test("production serves no interactive API documentation or schema", async ({ request }) => {
  // Phase 6 (security finding S13). Asked of the API directly: through Caddy these paths are
  // the interface's own routes, which answer with the single-page app.
  for (const path of ["/docs", "/redoc", "/openapi.json"]) {
    expect((await request.get(`${DIRECT_API}${path}`)).status(), path).toBe(404);
  }
  const throughSite = await request.get(`${SITE}/openapi.json`);
  expect(await throughSite.text()).not.toContain('"openapi"');
});

test("signs in over HTTPS with Secure, prefixed cookies and production headers", async ({ page, context }) => {
  // The sign-in page asks whether a session exists, which answers 401 before signing in; CSP
  // violations and page errors are still collected.
  const problems = await watchForProblems(page, true);
  const landing = await page.goto("/login");
  expect(landing?.headers()["strict-transport-security"]).toBe("max-age=31536000");
  expect(landing?.headers()["content-security-policy"]).toBe(CONTENT_SECURITY_POLICY);
  expect(landing?.headers().server).toBeUndefined();

  await signIn(page);
  await expect(page.getByRole("heading", { name: "Dashboard", level: 1 })).toBeVisible();
  const cookies = await context.cookies(`${SITE}/api/v1/auth/me`);
  const names = cookies.map((cookie) => cookie.name).sort();
  expect(names).toEqual(["__Host-finguard_csrf", "__Secure-finguard_session"]);
  const session = cookies.find((c) => c.name === "__Secure-finguard_session")!;
  const csrf = cookies.find((c) => c.name === "__Host-finguard_csrf")!;
  expect(session).toMatchObject({ secure: true, httpOnly: true, sameSite: "Strict", path: "/api" });
  expect(csrf).toMatchObject({ secure: true, httpOnly: false, sameSite: "Strict", path: "/" });
  expect(csrf.domain.startsWith(".")).toBe(false); // host-only, as __Host- requires

  // A full change through the interface: the cookie and CSRF path work under HTTPS.
  await page.getByRole("link", { name: "Transaction Analysis" }).click();
  await page.getByLabel("Amount").fill("1000000.00");
  await page.getByLabel("Transaction type").selectOption("TRANSFER");
  await page.getByLabel("Simulation step").fill("400");
  await page.getByRole("button", { name: "Score transaction" }).click();
  await expect(page.getByRole("article", { name: "Prediction result" })).toBeVisible();

  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  expect(await context.cookies(`${SITE}/api/v1/auth/me`)).toEqual([]);
  expect(problems.list).toEqual([]);
});

test("refuses changes without the CSRF token, from another origin, or over the wrong scheme", async ({ page }) => {
  await signIn(page);
  const token = await csrfToken(page);
  expect(token).not.toBe("");
  const post = (headers: Record<string, string>) => page.request.post(PREDICT, { data: INPUT, headers });

  expect((await post({ Origin: SITE })).status()).toBe(403);
  expect((await post({ Origin: SITE, "X-CSRF-Token": "forged" })).status()).toBe(403);
  expect((await post({ Origin: "https://evil.example", "X-CSRF-Token": token })).status()).toBe(403);
  expect((await post({ Origin: "http://127.0.0.1:8443", "X-CSRF-Token": token })).status()).toBe(403);
  expect((await post({ Origin: SITE, "X-CSRF-Token": token })).status()).toBe(201);
});

test("gives other origins no cross-origin access", async ({ request }) => {
  const preflight = await request.fetch(PREDICT, {
    method: "OPTIONS",
    headers: { Origin: "https://evil.example", "Access-Control-Request-Method": "POST" },
  });
  expect(preflight.headers()["access-control-allow-origin"]).toBeUndefined();
  const read = await request.get(`${SITE}/health`, { headers: { Origin: "https://evil.example" } });
  expect(read.headers()["access-control-allow-origin"]).toBeUndefined();
});

test("spoofed forwarded addresses cannot dodge the sign-in limit, through the proxy or around it", async ({ request }) => {
  for (const [base, name] of [
    [SITE, "logout"],
    [DIRECT_API, "expiry"],
  ]) {
    const { email } = prodlikeAccount(name);
    const attempt = (spoof: string) =>
      request.post(`${base}/api/v1/auth/session`, {
        data: { email, password: "not the right password" },
        headers: { Origin: SITE, "X-Forwarded-For": spoof },
      });
    // A different invented client address every time: if any were believed, no limit would bite.
    for (let index = 0; index < 5; index += 1) {
      expect((await attempt(`203.0.113.${index + 1}`)).status()).toBe(401);
    }
    expect((await attempt("198.51.100.77")).status(), `limit reached via ${base}`).toBe(429);
  }
});

test("the API trusts forwarded headers only from the proxy's fixed address", () => {
  const inspect = (container: string, format: string) =>
    execFileSync("docker", ["inspect", "--format", format, container], { encoding: "utf-8" }).trim();
  const caddy = inspect("finguard-caddy-prodlike-1", "{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}");
  expect(caddy.split(/\s+/).filter(Boolean)).toEqual([CADDY_ADDRESS]);
  const env = inspect("finguard-api-prodlike-1", "{{range .Config.Env}}{{println .}}{{end}}");
  expect(env).toContain(`TRUSTED_PROXY_IPS=${CADDY_ADDRESS}`);
  expect(env).toContain("APP_ENV=production");
  expect(env).not.toMatch(/SESSION_COOKIE_SECURE=false/i);
});
