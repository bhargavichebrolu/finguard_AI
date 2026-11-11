/**
 * The investigation workflow against the real API: queue filters, assignment, status changes
 * with confirmation, notes and history that persist, and ordering under concurrent updates.
 */
import { expect, test, type Page } from "@playwright/test";

import { FLAGGED_INPUT, account, apiCall, predictThroughApi, statePath } from "./support";

test.use({ storageState: statePath("investigator") });

interface HistoryEntry {
  from_status: string | null;
  to_status: string;
  created_at: string;
}

async function openNewCase(page: Page): Promise<{ id: string; externalId: string }> {
  await page.goto("/investigations");
  const flagged = await predictThroughApi(page, FLAGGED_INPUT);
  expect(flagged.investigation_status).toBe("NEW");
  return { id: flagged.investigation_id!, externalId: flagged.external_transaction_id };
}

function panel(page: Page) {
  return page.getByRole("region", { name: "Investigation" });
}

test("filters the queue by status and by assignment", async ({ page }) => {
  const { id, externalId } = await openNewCase(page);
  await page.goto("/investigations");
  const queue = page.getByRole("table", { name: "Investigation queue" });
  await page.getByLabel("Status").selectOption("NEW");
  await expect(queue.getByRole("row", { name: new RegExp(externalId) })).toBeVisible();

  await page.getByLabel("Status").selectOption("CLOSED");
  await expect(queue.getByRole("row", { name: new RegExp(externalId) })).toHaveCount(0);

  await page.getByLabel("Status").selectOption("");
  await page.getByLabel("Assigned to me").check();
  await expect(page.getByText(new RegExp(externalId))).toHaveCount(0);

  expect((await apiCall(page, "PATCH", `/api/v1/investigations/${id}`, { assigned_user_id: (await me(page)).id })).status()).toBe(200);
  await page.getByLabel("Assigned to me").uncheck();
  await page.getByLabel("Assigned to me").check();
  await expect(page.getByRole("table", { name: "Investigation queue" }).getByRole("row", { name: new RegExp(externalId) })).toBeVisible();
});

async function me(page: Page): Promise<{ id: string; email: string }> {
  return (await (await apiCall(page, "GET", "/api/v1/auth/me")).json()) as { id: string; email: string };
}

test("assigns a case to a colleague, to me and to nobody", async ({ page }) => {
  const { id } = await openNewCase(page);
  await page.goto(`/investigations?open=${id}`);
  const caseFile = panel(page);
  const colleague = account("colleague").email;
  const mine = account("investigator").email;

  await expect(caseFile.locator(".assignee .muted")).toHaveText("Nobody");
  await caseFile.getByLabel("Assigned to").selectOption({ label: `${colleague} (Investigator)` });
  await expect(caseFile.locator(".assignee .muted")).toHaveText(colleague);

  await caseFile.getByRole("button", { name: "Assign to me" }).click();
  await expect(caseFile.locator(".assignee .muted")).toHaveText(mine);
  await expect(caseFile.getByRole("button", { name: "Assign to me" })).toHaveCount(0);

  await page.reload();
  await expect(panel(page).locator(".assignee .muted")).toHaveText(mine);
  await panel(page).getByLabel("Assigned to").selectOption("");
  await expect(panel(page).locator(".assignee .muted")).toHaveText("Nobody");

  // Only active investigators and administrators can be chosen.
  const options = await panel(page).getByLabel("Assigned to").locator("option").allInnerTexts();
  expect(options.some((text) => text.includes("(Analyst)") || text.includes("(Demo)"))).toBe(false);
  const refused = await apiCall(page, "PATCH", `/api/v1/investigations/${id}`, { assigned_user_id: (await analystId(page)) });
  expect(refused.status()).toBe(422);
});

async function analystId(page: Page): Promise<string> {
  const context = await page.context().browser()!.newContext({ storageState: statePath("analyst") });
  const analystPage = await context.newPage();
  const id = (await me(analystPage)).id;
  await context.close();
  return id;
}

test("changes status, asks before concluding, and keeps the history", async ({ page }) => {
  const { id } = await openNewCase(page);
  await page.goto(`/investigations?open=${id}`);
  const caseFile = panel(page);

  await caseFile.getByLabel("Change status").selectOption("UNDER_REVIEW");
  // Each step of the first change is checked on its own: the click sends the change, the API
  // accepts it, then the page shows it. This test failed once in Firefox with the badge still
  // "New" and could not be reproduced (Phase 5 gate investigation), so if it recurs, the failing
  // line says which step broke: no request, a refusal, or a page that did not show the answer.
  const isStatusChange = (request: { method(): string; url(): string }) =>
    request.method() === "PATCH" && new URL(request.url()).pathname === `/api/v1/investigations/${id}`;
  const [request] = await Promise.all([
    page.waitForRequest(isStatusChange, { timeout: 10_000 }),
    caseFile.getByRole("button", { name: "Update status" }).click(),
  ]);
  const response = await request.response();
  expect(response?.status(), "the API's answer to the status change").toBe(200);
  expect(((await response!.json()) as { status: string }).status).toBe("UNDER_REVIEW");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(caseFile.locator(".badge-status").first()).toHaveText("Under review");

  for (const [value, label] of [["CLOSED", "closed"], ["FALSE_ALARM", "false alarm"]]) {
    await caseFile.getByLabel("Change status").selectOption(value);
    await caseFile.getByRole("button", { name: "Update status" }).click();
    const dialog = page.getByRole("dialog", { name: `Mark as ${label}?` });
    await expect(dialog).toContainText("It does not change the model's score or decision");
    await dialog.getByRole("button", { name: "Cancel" }).click();
    await expect(dialog).toHaveCount(0);
    await expect(caseFile.locator(".badge-status").first()).toHaveText("Under review");
  }
  // Escape also backs out.
  await caseFile.getByRole("button", { name: "Update status" }).click();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);

  await caseFile.getByLabel("Change status").selectOption("CLOSED");
  await caseFile.getByRole("button", { name: "Update status" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Mark as closed" }).click();
  await expect(caseFile.locator(".badge-status").first()).toHaveText("Closed");

  await page.reload();
  const history = panel(page).getByRole("listitem").filter({ hasText: /Opened as|to / });
  await expect(panel(page).locator(".timeline li")).toHaveCount(3);
  await expect(panel(page).locator(".timeline li").nth(0)).toContainText("Opened as New");
  await expect(panel(page).locator(".timeline li").nth(1)).toContainText("New to Under review");
  await expect(panel(page).locator(".timeline li").nth(2)).toContainText("Under review to Closed");
  expect(await history.count()).toBeGreaterThanOrEqual(3);
});

test("adds trimmed notes that persist", async ({ page }) => {
  const { id } = await openNewCase(page);
  await page.goto(`/investigations?open=${id}`);
  const caseFile = panel(page);
  await expect(caseFile.getByText("No notes yet.")).toBeVisible();
  await expect(caseFile.getByRole("button", { name: "Add note" })).toBeDisabled();
  await caseFile.getByLabel("Add a note").fill("   ");
  await expect(caseFile.getByRole("button", { name: "Add note" })).toBeDisabled();
  await caseFile.getByLabel("Add a note").fill("  Checked the counterparty history.  ");
  await expect(caseFile.getByText("37 of 5,000 characters")).toBeVisible();
  await caseFile.getByRole("button", { name: "Add note" }).click();
  await expect(caseFile.locator(".notes li p")).toHaveText(["Checked the counterparty history."]);
  await expect(caseFile.getByLabel("Add a note")).toHaveValue("");

  await page.reload();
  await expect(panel(page).locator(".notes li p")).toHaveText(["Checked the counterparty history."]);
});

test("keeps history in order under concurrent updates from two people", async ({ page, browser }) => {
  const { id } = await openNewCase(page);
  const other = await browser.newContext({ storageState: statePath("colleague") });
  const colleaguePage = await other.newPage();
  await colleaguePage.goto("/investigations");

  const targets = ["UNDER_REVIEW", "ESCALATED", "UNDER_REVIEW", "ESCALATED", "UNDER_REVIEW", "ESCALATED", "UNDER_REVIEW", "ESCALATED"];
  const responses = await Promise.all(
    targets.flatMap((status, index) => [
      apiCall(index % 2 === 0 ? page : colleaguePage, "PATCH", `/api/v1/investigations/${id}`, { status }),
      apiCall(index % 2 === 0 ? colleaguePage : page, "POST", `/api/v1/investigations/${id}/notes`, { note: `Concurrent note ${index}` }),
    ]),
  );
  expect(responses.map((response) => response.status()).sort()).toEqual([...Array(8).fill(200), ...Array(8).fill(201)].sort());
  await other.close();

  const detail = (await (await apiCall(page, "GET", `/api/v1/investigations/${id}`)).json()) as {
    status: string;
    history: HistoryEntry[];
    notes: { note: string }[];
  };
  const history = detail.history;
  expect(history[0]).toMatchObject({ from_status: null, to_status: "NEW" });
  for (let index = 1; index < history.length; index += 1) {
    // Each change starts from where the previous one ended, and time never runs backwards.
    expect(history[index].from_status).toBe(history[index - 1].to_status);
    expect(Date.parse(history[index].created_at)).toBeGreaterThanOrEqual(Date.parse(history[index - 1].created_at));
  }
  expect(history[history.length - 1].to_status).toBe(detail.status);
  expect(new Set(detail.notes.map((note) => note.note)).size).toBe(8);

  await page.goto(`/investigations?open=${id}`);
  await expect(panel(page).locator(".timeline li")).toHaveCount(history.length);
  await expect(panel(page).locator(".notes li")).toHaveCount(8);
});

test("refuses a change made from a stale page, shows what changed, then allows a fresh decision", async ({ page, browser }) => {
  // Phase 5 M7: without the expected status, this page would have closed the case over the
  // colleague's escalation without either of them knowing.
  const { id } = await openNewCase(page);
  await page.goto(`/investigations?open=${id}`);
  const caseFile = panel(page);
  await expect(caseFile.locator(".badge-status").first()).toHaveText("New");

  const colleague = await browser.newContext({ storageState: statePath("colleague") });
  const other = await colleague.newPage();
  await other.goto("/investigations");
  expect((await apiCall(other, "PATCH", `/api/v1/investigations/${id}`, { status: "ESCALATED" })).status()).toBe(200);
  await colleague.close();

  await caseFile.getByLabel("Change status").selectOption("CLOSED");
  await caseFile.getByRole("button", { name: "Update status" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Mark as closed" }).click();
  await expect(caseFile.getByRole("alert")).toContainText(
    "Someone else changed this investigation: its status is now Escalated. Review it and try again.",
  );
  await expect(caseFile.locator(".badge-status").first()).toHaveText("Escalated");
  await expect(caseFile.locator(".timeline li")).toHaveCount(2);
  await expect(caseFile.locator(".timeline li").nth(1)).toContainText("New to Escalated");

  await caseFile.getByLabel("Change status").selectOption("CLOSED");
  await caseFile.getByRole("button", { name: "Update status" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Mark as closed" }).click();
  await expect(caseFile.locator(".badge-status").first()).toHaveText("Closed");
  await expect(caseFile.locator(".timeline li")).toHaveCount(3);
  await expect(caseFile.locator(".timeline li").nth(2)).toContainText("Escalated to Closed");
});
