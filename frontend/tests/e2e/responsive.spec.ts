/**
 * Layout and accessibility at desktop (1440 x 900), tablet (768 x 1024) and mobile (390 x 844):
 * no horizontal scrolling, no automated WCAG 2.2 A/AA violations, no Content Security Policy
 * violations, the top bar on one line, the navigation menu, keyboard use, visible focus,
 * modal dialogs and touch target sizes. Screenshots are saved for the gate report.
 */
import path from "node:path";

import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page, type TestInfo } from "@playwright/test";

import {
  FLAGGED_INPUT,
  NO_SESSION,
  SCREENSHOT_DIR,
  UNFLAGGED_INPUT,
  predictThroughApi,
  statePath,
  watchForProblems,
} from "./support";

const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];
const PAGES = [
  { path: "/dashboard", heading: "Dashboard" },
  { path: "/analyse", heading: "Transaction Analysis" },
  { path: "/batches", heading: "CSV Batch Analysis" },
  { path: "/transactions", heading: "Transaction Explorer" },
  { path: "/investigations", heading: "Investigation Centre" },
  { path: "/models", heading: "Model Performance" },
  { path: "/explainability", heading: "Explainable AI" },
  { path: "/reports", heading: "Reports" },
  { path: "/settings", heading: "Settings" },
  { path: "/system", heading: "System Information" },
];

function narrow(testInfo: TestInfo): boolean {
  return testInfo.project.name !== "desktop";
}

async function settle(page: Page, heading: string): Promise<void> {
  await expect(page.getByRole("heading", { name: heading, level: 1 })).toBeVisible();
  await page.waitForLoadState("networkidle");
  await expect(page.locator(".loading-state, [aria-busy='true']")).toHaveCount(0);
}

/** Fail with a readable list of violations, never by switching rules off. */
async function expectNoAxeViolations(page: Page): Promise<void> {
  const results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();
  const summary = results.violations.map((violation) => ({
    rule: violation.id,
    impact: violation.impact,
    help: violation.help,
    targets: violation.nodes.slice(0, 5).map((node) => node.target.join(" ")),
  }));
  expect(summary).toEqual([]);
}

/**
 * No sideways scrolling. On phones a too-wide element can also widen the layout viewport itself
 * (an overflowing select did), so the viewport is checked against the device width as well.
 */
async function expectNoHorizontalScroll(page: Page): Promise<void> {
  const device = page.viewportSize()!.width;
  const measured = await page.evaluate(() => ({
    overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    layout: window.innerWidth,
  }));
  expect(measured.overflow, "horizontal overflow in CSS pixels").toBeLessThanOrEqual(0);
  expect(measured.layout, "layout viewport width").toBe(device);
}

async function screenshot(page: Page, testInfo: TestInfo, name: string): Promise<void> {
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, `${testInfo.project.name}-${name}.png`), fullPage: true });
}

/** Every visible control is at least 24 x 24 CSS pixels (WCAG 2.2 target size, minimum). */
async function expectTouchTargets(page: Page): Promise<void> {
  const small = await page.evaluate(() => {
    const controls = document.querySelectorAll<HTMLElement>("button, a[href], input, select, textarea, summary, [role='button']");
    return Array.from(controls)
      .filter((element) => {
        const box = element.getBoundingClientRect();
        const style = getComputedStyle(element);
        const shown = box.width > 0 && box.height > 0 && style.visibility !== "hidden";
        const inView = box.right > 0 && box.left < window.innerWidth;
        const inlineTextLink = element.tagName === "A" && style.display === "inline";
        return shown && inView && !inlineTextLink && (box.width < 24 || box.height < 24);
      })
      .map((element) => `${element.tagName.toLowerCase()} "${(element.textContent ?? element.getAttribute("aria-label") ?? "").trim().slice(0, 30)}"`);
  });
  expect(small).toEqual([]);
}

test.describe("signed-in pages", () => {
  test.use({ storageState: statePath("admin") });

  // Tables, badges and row buttons are only checked if there are rows, so make sure there are.
  test.beforeAll(async ({ browser }) => {
    const context = await browser.newContext({ storageState: statePath("admin") });
    const page = await context.newPage();
    await page.goto("/dashboard");
    await predictThroughApi(page, FLAGGED_INPUT);
    await predictThroughApi(page, UNFLAGGED_INPUT);
    await context.close();
  });

  for (const target of PAGES) {
    test(`${target.heading}: fits, has no automated WCAG violations and no CSP errors`, async ({ page }, testInfo) => {
      const problems = await watchForProblems(page);
      await page.goto(target.path);
      await settle(page, target.heading);
      await expectNoHorizontalScroll(page);
      await expectNoAxeViolations(page);
      await expectTouchTargets(page);
      await screenshot(page, testInfo, target.path.slice(1));
      expect(problems.list).toEqual([]);
    });
  }

  test("an open investigation and its confirmation dialog fit and pass the checks", async ({ page }, testInfo) => {
    await page.goto("/investigations");
    const flagged = await predictThroughApi(page, FLAGGED_INPUT);
    await page.goto(`/investigations?open=${flagged.investigation_id}`);
    const panel = page.getByRole("region", { name: "Investigation" });
    await expect(panel.getByRole("heading", { name: "Status history" })).toBeVisible();
    await expectNoHorizontalScroll(page);
    await expectNoAxeViolations(page);
    await panel.getByLabel("Change status").selectOption("FALSE_ALARM");
    await panel.getByRole("button", { name: "Update status" }).click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await expectNoHorizontalScroll(page);
    await expectNoAxeViolations(page);
    await screenshot(page, testInfo, "investigation-dialog");
    await page.keyboard.press("Escape");
  });

  test("a chart switches to its table by keyboard", async ({ page }) => {
    await page.goto("/models");
    await settle(page, "Model Performance");
    const toggle = page.getByRole("button", { name: "Show table" }).first();
    await toggle.focus();
    await page.keyboard.press("Enter");
    await expect(page.getByRole("button", { name: "Show chart" }).first()).toBeFocused();
    await expect(page.getByRole("table", { name: "PR-AUC by family (validation)" })).toBeVisible();
    await expectNoHorizontalScroll(page);
  });

  test("the top bar stays on one line and inside the screen", async ({ page }) => {
    await page.goto("/dashboard");
    await settle(page, "Dashboard");
    const topbar = page.locator("header.topbar");
    // Count the lines the text itself occupies. A flex item reports one box even when its
    // text wraps, so the element's own rectangles cannot detect wrapping.
    const textLines = (element: Element) => {
      const range = document.createRange();
      range.selectNodeContents(element);
      return new Set(Array.from(range.getClientRects()).map((box) => Math.round(box.top))).size;
    };
    expect(await topbar.locator(".brand span").evaluate(textLines), "FinGuard AI on one line").toBe(1);
    expect(await topbar.locator(".topbar-user .badge").evaluate(textLines), "role on one line").toBe(1);
    const signOut = topbar.getByRole("button", { name: "Sign out" });
    await expect(signOut).toBeVisible();
    expect(await signOut.locator(".sign-out-label").evaluate(textLines), "Sign out on one line").toBe(1);
    const buttonBox = await signOut.boundingBox();
    expect(buttonBox!.height).toBeGreaterThanOrEqual(24);
    expect(buttonBox!.width).toBeGreaterThanOrEqual(24);
    const height = await topbar.evaluate((element) => element.getBoundingClientRect().height);
    const declared = await topbar.evaluate((element) => parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--topbar-height")) || element.getBoundingClientRect().height);
    expect(height).toBeLessThanOrEqual(declared + 1);
    const outside = await topbar.evaluate((element) =>
      Array.from(element.querySelectorAll<HTMLElement>("*")).filter((child) => {
        const box = child.getBoundingClientRect();
        return box.width > 0 && (box.right > window.innerWidth + 0.5 || box.left < -0.5);
      }).length,
    );
    expect(outside).toBe(0);
  });

  test("the navigation menu opens, works by keyboard, and hides its links when closed", async ({ page }, testInfo) => {
    await page.goto("/dashboard");
    await settle(page, "Dashboard");
    // Located by id: while the menu is closed on narrow screens it is (correctly) absent from the
    // accessibility tree, so a role query would not find it.
    const navigation = page.locator("#main-navigation");
    const explorer = navigation.getByRole("link", { name: "Transaction Explorer" });
    if (!narrow(testInfo)) {
      await expect(explorer).toBeInViewport();
      await page.getByRole("button", { name: "Collapse navigation" }).click();
      await expect(navigation.getByRole("link", { name: "Transaction Explorer" })).toBeVisible();
      await expectNoAxeViolations(page);
      await page.getByRole("button", { name: "Expand navigation" }).click();
      return;
    }
    const menu = page.getByRole("button", { name: "Open navigation" });
    await expect(menu).toHaveAttribute("aria-expanded", "false");
    await expect(explorer).toBeHidden();

    // While closed, Tab must never land on a link the reader cannot see.
    for (let presses = 0; presses < 12; presses += 1) {
      await page.keyboard.press("Tab");
      expect(await navigation.evaluate((element) => element.contains(document.activeElement))).toBe(false);
    }

    await menu.click();
    await expect(menu).toHaveAttribute("aria-expanded", "true");
    await expect(explorer).toBeInViewport();
    await expectNoAxeViolations(page);
    await screenshot(page, testInfo, "menu-open");
    await page.keyboard.press("Escape");
    await expect(menu).toHaveAttribute("aria-expanded", "false");
    await expect(menu).toBeFocused();

    await menu.click();
    await explorer.click();
    await expect(page.getByRole("heading", { name: "Transaction Explorer", level: 1 })).toBeVisible();
    await expect(menu).toHaveAttribute("aria-expanded", "false");
    await expect(explorer).toBeHidden();
  });

  test("the skip link and focus indicator work from the keyboard", async ({ page }) => {
    await page.goto("/dashboard");
    await settle(page, "Dashboard");
    await page.keyboard.press("Tab");
    const skip = page.getByRole("link", { name: "Skip to content" });
    await expect(skip).toBeFocused();
    await expect(skip).toBeInViewport();
    await page.keyboard.press("Enter");
    await expect(page.locator("#main-content")).toBeFocused();

    await page.getByRole("button", { name: "Sign out" }).focus();
    await page.keyboard.press("Shift+Tab");
    await page.keyboard.press("Tab");
    const indicator = await page.evaluate(() => {
      const style = getComputedStyle(document.activeElement as Element);
      return { outline: style.outlineStyle, width: parseFloat(style.outlineWidth), shadow: style.boxShadow };
    });
    expect(indicator.outline !== "none" && indicator.width >= 2 ? true : indicator.shadow !== "none").toBe(true);
  });

  test("a confirmation dialog keeps focus inside and returns it when closed", async ({ page }) => {
    await page.goto("/settings");
    await settle(page, "Settings");
    const save = page.getByRole("button", { name: "Save boundary" });
    await save.click();
    const dialog = page.getByRole("dialog", { name: "Change the high risk boundary?" });
    await expect(dialog).toBeVisible();
    await expect(dialog.getByRole("button", { name: "Cancel" })).toBeFocused();
    await expect(dialog).toHaveAttribute("aria-modal", "true");
    for (let presses = 0; presses < 4; presses += 1) {
      await page.keyboard.press("Tab");
      expect(await dialog.evaluate((element) => element.contains(document.activeElement))).toBe(true);
    }
    await page.keyboard.press("Shift+Tab");
    expect(await dialog.evaluate((element) => element.contains(document.activeElement))).toBe(true);
    await page.keyboard.press("Escape");
    await expect(dialog).toHaveCount(0);
    await expect(save).toBeFocused();
  });
});

test.describe("sign-in page", () => {
  test.use({ storageState: NO_SESSION });

  test("fits, has no automated WCAG violations, and shows field errors accessibly", async ({ page }, testInfo) => {
    const problems = await watchForProblems(page, true);
    await page.goto("/login");
    await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
    await expectNoHorizontalScroll(page);
    await expectNoAxeViolations(page);
    await expectTouchTargets(page);
    await page.getByLabel("Email").fill("someone@example.com");
    await page.getByLabel("Password").fill("wrong-password-value");
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page.getByRole("alert")).toHaveText("Incorrect email or password.");
    await expectNoAxeViolations(page);
    await screenshot(page, testInfo, "login");
    expect(problems.list).toEqual([]);
  });
});
