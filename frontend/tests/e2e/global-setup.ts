/**
 * Runs once before the browser tests: check the test API is up, reseed the test database, and
 * prove the API on port 8011 reads that database by signing in with a freshly seeded account.
 */
import { request } from "@playwright/test";

import { API_URL, account, runDatabaseScript, ACCOUNTS_FILE } from "./support";

export default async function globalSetup(): Promise<void> {
  const api = await request.newContext();
  try {
    const health = await api.get(`${API_URL}/health`, { timeout: 5_000 }).catch(() => null);
    if (!health?.ok()) {
      throw new Error(`The browser-test API is not answering at ${API_URL}. Start it: python scripts/e2e_stack.py up`);
    }
    process.stdout.write(runDatabaseScript("seed", "--out", ACCOUNTS_FILE));

    // A fresh random password can only work if this API uses the database just seeded.
    const admin = account("admin");
    const signIn = await api.post(`${API_URL}/api/v1/auth/session`, {
      data: { email: admin.email, password: admin.password },
      headers: { Origin: "http://127.0.0.1:4173" },
    });
    if (signIn.status() !== 200) {
      throw new Error(`The API at ${API_URL} is not using the seeded test database (sign-in gave ${signIn.status()}).`);
    }
  } finally {
    await api.dispose();
  }
}
