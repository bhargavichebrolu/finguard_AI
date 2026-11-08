/** Model Performance, Reports and Settings, including administrator account management. */
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AxiosError, AxiosHeaders } from "axios";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { familyName, ruleName } from "../../src/pages/ModelPerformancePage";
import { REPORTS } from "../../src/pages/ReportsPage";
import { checkBoundary } from "../../src/pages/SettingsPage";
import { PAGES } from "../../src/pages/registry";
import { readBlobError, type User } from "../../src/services/endpoints";
import { SCORE_MEANING } from "../../src/components/ScoreDisclosure";
import { reportFixture, settingsFixture, TEST_NOTE_RECALL, userFixture } from "./fixtures";
import { renderApp } from "./render";
import { errorBody, server, state } from "./server";

beforeEach(() => {
  URL.createObjectURL = vi.fn(() => "blob:fixture");
  URL.revokeObjectURL = vi.fn();
  server.use(
    http.get("/api/v1/models/report", () => HttpResponse.json(reportFixture())),
    http.get("/api/v1/settings", () => HttpResponse.json(settingsFixture())),
  );
});

describe("navigation", () => {
  it("lists every page in PRD 7.4 order", () => {
    expect(PAGES.map((page) => page.label)).toEqual([
      "Dashboard",
      "Transaction Analysis",
      "CSV Batch Analysis",
      "Transaction Explorer",
      "Investigation Centre",
      "Model Performance",
      "Explainable AI",
      "Reports",
      "Settings",
      "System Information",
    ]);
  });
});

describe("Model Performance", () => {
  it("names families and threshold rules readably", () => {
    expect(familyName("logistic_regression")).toBe("Logistic Regression");
    expect(familyName("new_family")).toBe("New family");
    expect(ruleName("fpr_cap_0.005")).toBe("False positive rate at most 0.005");
    expect(ruleName("max_f2")).toBe("Highest F2");
  });

  it("shows the saved results from the report, with the disclosure", async () => {
    state.role = "analyst";
    renderApp("/models");
    expect(await screen.findByText("Fixture report note one.")).toBeInTheDocument();
    expect(screen.getByText(SCORE_MEANING)).toBeInTheDocument();
    expect(await screen.findByText(TEST_NOTE_RECALL)).toBeInTheDocument();

    const comparison = screen.getByRole("table", { name: "Model comparison on validation" });
    const xgboost = within(comparison).getByRole("row", { name: /XGBoost/ });
    expect(within(xgboost).getByText("Selected")).toBeInTheDocument();
    expect(within(xgboost).getByText("0.6111")).toBeInTheDocument();
    expect(within(within(comparison).getByRole("row", { name: /CatBoost/ })).getByText("Tied")).toBeInTheDocument();

    const test = screen.getByRole("table", { name: "Test, evaluated once" });
    expect(within(test).getByText("111")).toBeInTheDocument();
    expect(within(test).getByText("44,444")).toBeInTheDocument();

    const thresholds = screen.getByRole("table", { name: "Thresholds compared on validation" });
    expect(within(thresholds).getByText("Frozen threshold")).toBeInTheDocument();
    expect(within(thresholds).getByText("False positive rate at most 0.005")).toBeInTheDocument();
    expect(within(thresholds).getByText("PRD candidate 0.50")).toBeInTheDocument();
    expect(screen.getByText("Fixture objective sentence.", { exact: false })).toBeInTheDocument();

    const matrix = screen.getByRole("table", { name: "PR-AUC by family and imbalance strategy" });
    expect(within(matrix).getByText("0.5111")).toBeInTheDocument();
    expect(screen.getByText(/artifacts\/metrics\/fixture\.json/)).toBeInTheDocument();
  });

  it("filters the experiment history by stage", async () => {
    renderApp("/models");
    const history = await screen.findByRole("table", { name: "Recorded experiment runs" });
    expect(within(history).getByText("run-matrix-1")).toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText("Stage"), "tuning");
    expect(within(history).queryByText("run-matrix-1")).not.toBeInTheDocument();
    expect(within(history).getByText("run-tuning-1")).toBeInTheDocument();
  });

  it("shows a chart as a table on request", async () => {
    renderApp("/models");
    await screen.findByText("Fixture report note one.");
    const card = screen.getByRole("heading", { name: "PR-AUC by family (validation)" }).closest("article") as HTMLElement;
    await userEvent.click(within(card).getByRole("button", { name: "Show table" }));
    expect(within(card).getByRole("table")).toHaveTextContent("0.2333");
  });

  it("reports a failure to load the report", async () => {
    server.use(http.get("/api/v1/models/report", () => errorBody("Model report unavailable.", 503)));
    renderApp("/models");
    expect(await screen.findByText("Model report unavailable.")).toBeInTheDocument();
  });
});

describe("Reports", () => {
  it("downloads each report type from its path", async () => {
    state.role = "analyst";
    const requested: string[] = [];
    server.use(
      http.get("/api/v1/reports/export", ({ request }) => {
        requested.push(new URL(request.url).searchParams.get("report_type") ?? "");
        return new HttpResponse("a,b\n1,2\n", { headers: { "Content-Type": "text/csv" } });
      }),
    );
    renderApp("/reports");
    await screen.findByRole("heading", { name: "Reports" });
    expect(screen.getAllByRole("button", { name: /^Download/ })).toHaveLength(REPORTS.length);
    await userEvent.click(screen.getByRole("button", { name: "Download flag summary" }));
    await waitFor(() => expect(requested).toEqual(["flag_summary"]));
    expect(URL.createObjectURL).toHaveBeenCalled();
  });

  it("shows an error when a download fails", async () => {
    state.role = "analyst";
    server.use(http.get("/api/v1/reports/export", () => errorBody("Export failed.", 500)));
    renderApp("/reports");
    await userEvent.click(await screen.findByRole("button", { name: "Download model evaluation" }));
    // jsdom's XMLHttpRequest drops blob bodies, so only the status reaches the page here.
    expect(await screen.findByText(/server had a problem/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Download model evaluation" })).toBeEnabled();
  });

  it("reads the API's message out of a blob error body", async () => {
    const body = new Blob([JSON.stringify({ detail: "Export failed.", request_id: "req-9" })], { type: "application/json" });
    const caught = new AxiosError("failed", "ERR_BAD_RESPONSE", undefined, undefined, {
      status: 500,
      statusText: "",
      headers: {},
      config: { headers: new AxiosHeaders() },
      data: body,
    });
    const error = await readBlobError(caught);
    expect(error.message).toBe("Export failed.");
    expect(error.requestId).toBe("req-9");

    const unreadable = new AxiosError("failed", "ERR_BAD_RESPONSE", undefined, undefined, {
      status: 502,
      statusText: "",
      headers: {},
      config: { headers: new AxiosHeaders() },
      data: new Blob(["<html>"]),
    });
    expect((await readBlobError(unreadable)).message).toMatch(/server had a problem/);
  });

  it("is closed to the demo role", async () => {
    state.role = "demo";
    renderApp("/reports");
    expect(await screen.findByRole("heading", { name: /not available|permission|access/i })).toBeInTheDocument();
  });
});

describe("Settings", () => {
  it("checks the high risk boundary against the frozen threshold", () => {
    expect(checkBoundary("", 0.03)).toBe("Enter a number.");
    expect(checkBoundary("abc", 0.03)).toBe("Enter a number.");
    expect(checkBoundary("0.03", 0.03)).toMatch(/above the frozen threshold/);
    expect(checkBoundary("1.5", 0.03)).toMatch(/at most 1/);
    expect(checkBoundary("0.4", 0.03)).toBeNull();
  });

  it("shows settings read-only to an analyst", async () => {
    state.role = "analyst";
    renderApp("/settings");
    expect(await screen.findByText("Fixture bands: not calibrated.")).toBeInTheDocument();
    expect(screen.getByText(/cannot be changed/)).toBeInTheDocument();
    expect(screen.queryByLabelText("High risk boundary")).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Accounts" })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Change your password" })).toBeInTheDocument();
  });

  it("lets an administrator change the boundary after confirming", async () => {
    state.role = "admin";
    const patches: unknown[] = [];
    server.use(
      http.get("/api/v1/users", () => HttpResponse.json({ items: [], total: 0, limit: 20, offset: 0 })),
      http.patch("/api/v1/settings", async ({ request }) => {
        patches.push(await request.json());
        return HttpResponse.json({ ...settingsFixture(), high_risk_boundary: 0.45 });
      }),
    );
    renderApp("/settings");
    const input = await screen.findByLabelText("High risk boundary");
    await userEvent.clear(input);
    await userEvent.type(input, "0.01");
    await userEvent.click(screen.getByRole("button", { name: "Save boundary" }));
    expect(screen.getByText(/above the frozen threshold/)).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    await userEvent.clear(input);
    await userEvent.type(input, "0.45");
    await userEvent.click(screen.getByRole("button", { name: "Save boundary" }));
    const dialog = screen.getByRole("dialog");
    await userEvent.click(within(dialog).getByRole("button", { name: "Change boundary" }));
    await waitFor(() => expect(patches).toEqual([{ high_risk_boundary: 0.45 }]));
    expect(await screen.findByText(/^Saved\./)).toBeInTheDocument();
  });

  describe("account management", () => {
    const me = userFixture("admin");
    const other: User = { id: "77777777-7777-4777-8777-777777777777", email: "colleague@example.com", role: "analyst", is_active: true, created_at: "2026-11-08T09:00:00Z" };
    let patches: { id: string; body: unknown }[];
    let created: unknown[];

    beforeEach(() => {
      state.role = "admin";
      patches = [];
      created = [];
      const self: User = { id: me.id, email: me.email, role: me.role, is_active: true, created_at: me.created_at };
      server.use(
        http.get("/api/v1/users", () => HttpResponse.json({ items: [self, other], total: 2, limit: 20, offset: 0 })),
        http.patch("/api/v1/users/:id", async ({ params, request }) => {
          const body = await request.json();
          patches.push({ id: String(params.id), body });
          return HttpResponse.json({ ...other, ...(body as object) });
        }),
        http.post("/api/v1/users", async ({ request }) => {
          const body = (await request.json()) as { email: string };
          created.push(body);
          return HttpResponse.json({ ...other, id: "88888888-8888-4888-8888-888888888888", email: body.email }, { status: 201 });
        }),
      );
    });

    it("deactivates another account only after confirming, and never your own", async () => {
      renderApp("/settings");
      const table = await screen.findByRole("table", { name: "Accounts" });
      const ownRow = within(table).getByRole("row", { name: /admin@example\.com/ });
      expect(within(ownRow).getByRole("button", { name: "Deactivate" })).toBeDisabled();

      const row = within(table).getByRole("row", { name: /colleague@example\.com/ });
      await userEvent.click(within(row).getByRole("button", { name: "Deactivate" }));
      const dialog = screen.getByRole("dialog");
      expect(dialog).toHaveTextContent("colleague@example.com");
      await userEvent.click(within(dialog).getByRole("button", { name: "Deactivate" }));
      await waitFor(() => expect(patches).toEqual([{ id: other.id, body: { is_active: false } }]));
    });

    it("changes a role", async () => {
      renderApp("/settings");
      await userEvent.selectOptions(await screen.findByLabelText("Role for colleague@example.com"), "investigator");
      await waitFor(() => expect(patches).toEqual([{ id: other.id, body: { role: "investigator" } }]));
    });

    it("creates an account once the password is long enough", async () => {
      renderApp("/settings");
      await userEvent.type(await screen.findByLabelText("Email"), "new@example.com");
      await userEvent.type(screen.getByLabelText("Temporary password"), "short");
      const submit = screen.getByRole("button", { name: "Create account" });
      expect(submit).toBeDisabled();
      await userEvent.type(screen.getByLabelText("Temporary password"), " but now long enough");
      await userEvent.selectOptions(screen.getByLabelText("Role"), "investigator");
      await userEvent.click(submit);
      await waitFor(() =>
        expect(created).toEqual([{ email: "new@example.com", password: "short but now long enough", role: "investigator" }]),
      );
      expect(await screen.findByText(/Created new@example\.com/)).toBeInTheDocument();
    });
  });
});
