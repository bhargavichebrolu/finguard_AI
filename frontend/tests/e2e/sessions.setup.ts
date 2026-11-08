/**
 * Signs in once per main role through the real form and saves each browser state, so later
 * tests start signed in without repeating the form.
 */
import { test as setup } from "@playwright/test";

import { signInThroughForm, statePath, type AccountName } from "./support";

const ROLES: AccountName[] = ["admin", "investigator", "analyst", "demo", "colleague"];

for (const name of ROLES) {
  setup(`sign in as ${name}`, async ({ page }) => {
    await signInThroughForm(page, name);
    await page.context().storageState({ path: statePath(name) });
  });
}
