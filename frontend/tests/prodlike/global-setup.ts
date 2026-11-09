/**
 * Before the production-like tests: check the HTTPS site answers, reseed its own test database,
 * and prove the API behind Caddy reads that database by signing in with a fresh password.
 */
import { request } from "@playwright/test";

import { prodlikeAccount, PRODLIKE_ACCOUNTS, PRODLIKE_DB, SITE } from "./prodlike";
import { runDatabaseScript } from "../e2e/support";

export default async function globalSetup(): Promise<void> {
  const client = await request.newContext({ ignoreHTTPSErrors: true });
  try {
    const health = await client.get(`${SITE}/health`, { timeout: 5_000 }).catch(() => null);
    if (!health?.ok()) {
      throw new Error(`The production-like stack is not answering at ${SITE}. Start it: python scripts/prodlike_stack.py up`);
    }
    process.env.E2E_DB_NAME = PRODLIKE_DB;
    process.stdout.write(runDatabaseScript("seed", "--out", PRODLIKE_ACCOUNTS));
    const admin = prodlikeAccount("admin");
    const signIn = await client.post(`${SITE}/api/v1/auth/session`, {
      data: { email: admin.email, password: admin.password },
      headers: { Origin: SITE },
    });
    if (signIn.status() !== 200) {
      throw new Error(`The production-like API is not using ${PRODLIKE_DB} (sign-in gave ${signIn.status()}).`);
    }
  } finally {
    await client.dispose();
  }
}
