/**
 * What assistive technology is given (Phase 5 M6): the accessibility tree of key screens, compared
 * with the expected landmarks, headings, names, roles and states. This is evidence about the
 * information a screen reader receives, not about how a screen reader speaks it; that needs the
 * manual checklist in docs/accessibility/screen-reader-checklist.md.
 */
import { expect, test } from "@playwright/test";

import { NO_SESSION, statePath } from "./support";

test.describe("signed out", () => {
  test.use({ storageState: NO_SESSION });

  test("the sign-in page names its heading, fields, button and errors", async ({ page }) => {
    await page.goto("/login");
    await expect(page.locator("main")).toMatchAriaSnapshot(`
      - main:
        - heading "Sign in" [level=1]
        - text: Email
        - textbox "Email"
        - text: Password
        - textbox "Password"
        - button "Sign in" [disabled]
    `);
    await page.getByLabel("Email").fill("someone@example.com");
    await page.getByLabel("Password").fill("not-the-right-password");
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page.locator("main")).toMatchAriaSnapshot(`
      - main:
        - alert: Incorrect email or password.
        - button "Sign in"
    `);
  });
});

test.describe("signed in", () => {
  test.use({ storageState: statePath("admin") });

  test("the frame has a skip link, banner, navigation in order, main and the score disclosure", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page.getByRole("heading", { name: "Dashboard", level: 1 })).toBeVisible();
    await expect(page.locator("body")).toMatchAriaSnapshot(`
      - link "Skip to content"
      - banner:
        - text: FinGuard AI
        - button "Sign out"
      - navigation "Main navigation":
        - button "Collapse navigation" [expanded]
        - list:
          - listitem:
            - link "Dashboard"
          - listitem:
            - link "Transaction Analysis"
          - listitem:
            - link "CSV Batch Analysis"
          - listitem:
            - link "Transaction Explorer"
          - listitem:
            - link "Investigation Centre"
          - listitem:
            - link "Model Performance"
          - listitem:
            - link "Explainable AI"
          - listitem:
            - link "Reports"
          - listitem:
            - link "Settings"
          - listitem:
            - link "System Information"
      - main:
        - heading "Dashboard" [level=1]
        - complementary "How to read model scores":
          - paragraph: /not calibrated and are not the chance that a transaction is fraud/
    `);
  });

  test("the scoring form exposes names, the disabled destination and invalid fields", async ({ page }) => {
    await page.goto("/analyse");
    const form = page.getByRole("form", { name: "Transaction details" });
    await expect(form).toMatchAriaSnapshot(`
      - form "Transaction details":
        - heading "Transaction" [level=2]
        - textbox "Amount"
        - combobox "Transaction type"
        - combobox "Destination category" [disabled]
        - textbox "Simulation step"
        - textbox "Transaction identifier (optional)"
        - button "Score transaction"
    `);
    await form.getByRole("button", { name: "Score transaction" }).click();
    await expect(form.getByRole("textbox", { name: "Amount" })).toHaveAttribute("aria-invalid", "true");
    await expect(form.getByRole("textbox", { name: "Amount" })).toHaveAccessibleDescription(
      "Enter an amount above 0 with at most two decimal places.",
    );
  });

  test("a confirmation dialog is a named modal with its message and both choices", async ({ page }) => {
    await page.goto("/settings");
    await page.getByRole("button", { name: "Save boundary" }).click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toMatchAriaSnapshot(`
      - dialog "Change the high risk boundary?":
        - heading "Change the high risk boundary?" [level=2]
        - text: /will be labelled High/
        - button "Cancel"
        - button "Change boundary"
    `);
    await expect(dialog).toHaveAttribute("aria-modal", "true");
    await expect(dialog).toHaveAccessibleDescription(/will be labelled High/);
    await page.keyboard.press("Escape");
  });

  test("charts are hidden from assistive technology and offer a named table instead", async ({ page }) => {
    await page.goto("/models");
    const card = page.getByRole("article").filter({ has: page.getByRole("heading", { name: "PR-AUC by family (validation)" }) });
    await expect(card).toMatchAriaSnapshot(`
      - article:
        - heading "PR-AUC by family (validation)" [level=2]
        - button "Show table"
    `);
    await card.getByRole("button", { name: "Show table" }).click();
    await expect(card).toMatchAriaSnapshot(`
      - article:
        - heading "PR-AUC by family (validation)" [level=2]
        - button "Show chart" [pressed]
        - group "PR-AUC by family (validation), scrollable table":
          - table "PR-AUC by family (validation)":
            - rowgroup:
              - row "Family PR-AUC"
    `);
  });
});
