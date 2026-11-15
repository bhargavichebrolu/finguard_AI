/** The Investigation Centre: queue, detail, status changes with confirmation, notes, assignment. */
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";

import type { InvestigationDetail, InvestigationSummary } from "../../src/services/endpoints";
import { userFixture } from "./fixtures";
import { renderApp } from "./render";
import { errorBody, server, state } from "./server";

const ID = "55555555-5555-4555-8555-555555555555";
const SUMMARY: InvestigationSummary = {
  id: ID,
  status: "NEW",
  status_note: "Fixture workflow note.",
  assigned_user_id: null,
  prediction_id: "44444444-4444-4444-8444-444444444444",
  transaction_id: "33333333-3333-4333-8333-333333333333",
  external_transaction_id: "FIX-1",
  amount: 9000000,
  transaction_type: "TRANSFER",
  step: 5,
  model_score: 0.8377,
  score_is_calibrated: false,
  risk_level: "HIGH",
  prediction: "FLAG_FOR_REVIEW",
  model_version: "fraud_detector_v1",
  threshold_used: 0.03,
  created_at: "2026-11-08T10:00:00Z",
  updated_at: "2026-11-08T10:00:00Z",
};

let detail: InvestigationDetail;
let patches: Record<string, unknown>[];
let listUrls: URL[];

beforeEach(() => {
  patches = [];
  listUrls = [];
  detail = {
    id: ID,
    prediction_id: SUMMARY.prediction_id,
    status: "NEW",
    assigned_user_id: null,
    created_at: "2026-11-08T10:00:00Z",
    updated_at: "2026-11-08T10:00:00Z",
    notes: [],
    history: [{ from_status: null, to_status: "NEW", changed_by: null, created_at: "2026-11-08T10:00:00Z" }],
  };
  state.role = "investigator";
  server.use(
    http.get("/api/v1/investigations", ({ request }) => {
      listUrls.push(new URL(request.url));
      return HttpResponse.json({ items: [{ ...SUMMARY, status: detail.status }], total: 1, limit: 25, offset: 0 });
    }),
    http.get("/api/v1/investigations/:id", () => HttpResponse.json(detail)),
    http.patch("/api/v1/investigations/:id", async ({ request }) => {
      const change = (await request.json()) as Record<string, unknown>;
      patches.push(change);
      if (typeof change.status === "string") {
        detail = {
          ...detail,
          status: change.status as InvestigationDetail["status"],
          history: [...detail.history, { from_status: detail.status, to_status: change.status as InvestigationDetail["status"], changed_by: "me", created_at: "2026-11-08T11:00:00Z" }],
        };
      }
      if ("assigned_user_id" in change) detail = { ...detail, assigned_user_id: change.assigned_user_id as string | null };
      return HttpResponse.json(detail);
    }),
    http.post("/api/v1/investigations/:id/notes", async ({ request }) => {
      const { note } = (await request.json()) as { note: string };
      const created = { id: `n${detail.notes.length}`, user_id: "me", note, created_at: "2026-11-08T12:00:00Z" };
      detail = { ...detail, notes: [...detail.notes, created] };
      return HttpResponse.json(created, { status: 201 });
    }),
    http.get("/api/v1/users/assignable", () =>
      HttpResponse.json([{ id: "77777777-7777-4777-8777-777777777777", email: "colleague@example.com", role: "investigator" }]),
    ),
  );
});

async function openCase() {
  renderApp("/investigations");
  await userEvent.click(await screen.findByRole("button", { name: "Open" }));
  return screen.findByRole("region", { name: "Investigation" });
}

describe("investigation centre", () => {
  it("lists the queue with the workflow statement", async () => {
    renderApp("/investigations");
    expect(await screen.findByText("FIX-1")).toBeInTheDocument();
    expect(screen.getAllByText(/not verified criminal findings/).length).toBeGreaterThan(0);
  });

  it("filters by status and by assignment to me", async () => {
    renderApp("/investigations");
    await screen.findByText("FIX-1");
    await userEvent.selectOptions(screen.getByLabelText("Status"), "ESCALATED");
    await userEvent.click(screen.getByLabelText("Assigned to me"));
    await waitFor(() => expect(listUrls.at(-1)?.searchParams.get("assigned_user_id")).toBe(userFixture("investigator").id));
    expect(listUrls.at(-1)?.searchParams.get("investigation_status")).toBe("ESCALATED");
  });

  it("opens a case directly from a link", async () => {
    renderApp(`/investigations?open=${ID}`);
    expect(await screen.findByRole("region", { name: "Investigation" })).toBeInTheDocument();
  });

  it("changes status without confirmation when the review continues", async () => {
    const panel = await openCase();
    await userEvent.selectOptions(within(panel).getByLabelText("Change status"), "UNDER_REVIEW");
    await userEvent.click(within(panel).getByRole("button", { name: "Update status" }));
    await waitFor(() => expect(patches).toEqual([{ status: "UNDER_REVIEW", expected_status: "NEW" }]));
    expect(await within(panel).findByText(/New to Under review/)).toBeInTheDocument();
  });

  it("asks before closing a case, and does nothing if cancelled", async () => {
    const panel = await openCase();
    await userEvent.selectOptions(within(panel).getByLabelText("Change status"), "FALSE_ALARM");
    await userEvent.click(within(panel).getByRole("button", { name: "Update status" }));
    const dialog = screen.getByRole("dialog", { name: "Mark as false alarm?" });
    expect(dialog).toHaveTextContent("does not change the model's score or decision");
    await userEvent.click(within(dialog).getByRole("button", { name: "Cancel" }));
    expect(patches).toEqual([]);
    await userEvent.click(within(panel).getByRole("button", { name: "Update status" }));
    await userEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Mark as false alarm" }));
    await waitFor(() => expect(patches).toEqual([{ status: "FALSE_ALARM", expected_status: "NEW" }]));
  });

  it("adds a trimmed note and shows it", async () => {
    const panel = await openCase();
    const button = within(panel).getByRole("button", { name: "Add note" });
    expect(button).toBeDisabled();
    await userEvent.type(within(panel).getByLabelText("Add a note"), "   Checked the amount.  ");
    await userEvent.click(button);
    expect(await within(panel).findByText("Checked the amount.")).toBeInTheDocument();
    expect(within(panel).getByLabelText("Add a note")).toHaveValue("");
  });

  it("assigns to me, to a colleague and to nobody", async () => {
    const panel = await openCase();
    await userEvent.click(within(panel).getByRole("button", { name: "Assign to me" }));
    await waitFor(() => expect(patches.at(-1)).toEqual({ assigned_user_id: userFixture("investigator").id }));
    await userEvent.selectOptions(within(panel).getByLabelText("Assigned to"), "77777777-7777-4777-8777-777777777777");
    await waitFor(() => expect(patches.at(-1)).toEqual({ assigned_user_id: "77777777-7777-4777-8777-777777777777" }));
    await userEvent.selectOptions(within(panel).getByLabelText("Assigned to"), "");
    await waitFor(() => expect(patches.at(-1)).toEqual({ assigned_user_id: null }));
  });

  it("shows the API's refusal of an action", async () => {
    server.use(http.patch("/api/v1/investigations/:id", () => errorBody("The assignee must be an active investigator or administrator.", 422)));
    const panel = await openCase();
    await userEvent.click(within(panel).getByRole("button", { name: "Assign to me" }));
    expect(await within(panel).findByText(/must be an active investigator/)).toBeInTheDocument();
  });

  it("is read-only for analysts", async () => {
    state.role = "analyst";
    const panel = await openCase();
    expect(within(panel).getByText(/Investigators and administrators can change them/)).toBeInTheDocument();
    expect(within(panel).queryByLabelText("Change status")).not.toBeInTheDocument();
    expect(within(panel).queryByLabelText("Add a note")).not.toBeInTheDocument();
  });

  it("is not available to demo users", async () => {
    state.role = "demo";
    renderApp("/investigations");
    expect(await screen.findByRole("heading", { name: "Not available for your role" })).toBeInTheDocument();
  });
});
