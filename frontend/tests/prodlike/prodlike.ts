/**
 * Shared values for the production-like tests: the HTTPS site, the API's direct address, the
 * database and the seeded accounts (kept apart from the browser-test accounts).
 */
import { readFileSync } from "node:fs";
import path from "node:path";

import { STATE_DIR, type Account } from "../e2e/support";

export const SITE = "https://127.0.0.1:8443";
export const PLAIN_HTTP = "http://127.0.0.1:8082";
export const DIRECT_API = "http://127.0.0.1:8012";
export const PRODLIKE_DB = "finguard_prodlike_test";
export const PRODLIKE_ACCOUNTS = path.join(STATE_DIR, "prodlike-accounts.json");
export const CADDY_ADDRESS = "172.30.250.10";

/** A seeded account on the production-like database. The password is never logged. */
export function prodlikeAccount(name: string): Account {
  return (JSON.parse(readFileSync(PRODLIKE_ACCOUNTS, "utf-8")) as Record<string, Account>)[name];
}
