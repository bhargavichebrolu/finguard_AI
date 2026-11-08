/** Dashboard, Transaction Analysis and Explainable AI, against the mock API. */
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { destinationFor, validateForm } from "../../src/pages/TransactionAnalysisPage";
import { featureImportanceFixture, predictionFixture, summaryFixture, TEST_NOTE_FPR } from "./fixtures";
import { renderApp } from "./render";
import { errorBody, server } from "./server";

function useSummary(summary = summaryFixture()) {
  server.use(http.get("/api/v1/reports/summary", () => HttpResponse.json(summary)));
}

describe("dashboard", () => {
  it("shows the three kinds of information in separate sections, with API figures", async () => {
    useSummary();
    renderApp("/dashboard");
    expect(await screen.findByRole("heading", { name: "Model flags" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Investigation workflow" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Uploaded labels" })).toBeInTheDocument();
    const tile = screen.getAllByText("Flagged for review").find((node) => node.classList.contains("stat-label"));
    expect(tile?.closest(".stat-tile")).toHaveTextContent("7");
    expect(screen.getByText(/Of analysed records; not a fraud rate/)).toBeInTheDocument();
  });

  it("shows the disclosure from the API on the dashboard", async () => {
    useSummary();
    renderApp("/dashboard");
    expect(await screen.findByText(TEST_NOTE_FPR)).toBeInTheDocument();
  });

  it("shows the model performance summary from the metrics response", async () => {
    useSummary();
    renderApp("/dashboard");
    const card = (await screen.findByRole("heading", { name: "Model performance summary" })).closest("article")!;
    // Overall and normal-step recall are both 0.5 in the fixture.
    expect(within(card).getAllByText("50.0%")).toHaveLength(2);
    expect(within(card).getByText("40.0%")).toBeInTheDocument();
    expect(within(card).getByText("Target was 0.1%")).toBeInTheDocument();
  });

  it("offers each chart as a table", async () => {
    useSummary();
    renderApp("/dashboard");
    const card = (await screen.findByRole("heading", { name: "Risk bands" })).closest("article")!;
    await userEvent.click(within(card).getByRole("button", { name: "Show table" }));
    const table = within(card).getByRole("table");
    expect(within(table).getByText("Medium")).toBeInTheDocument();
    expect(within(card).getByRole("button", { name: "Show chart" })).toHaveAttribute("aria-pressed", "true");
  });

  it("explains an empty scope instead of drawing empty charts", async () => {
    useSummary(summaryFixture({ empty: true }));
    renderApp("/dashboard");
    expect(await screen.findByText("No transactions have been analysed in this scope yet.")).toBeInTheDocument();
    expect(screen.getByText("No predictions yet")).toBeInTheDocument();
    expect(screen.getByText("No labels have been supplied.")).toBeInTheDocument();
  });

  it("labels demo statistics as demo", async () => {
    useSummary(summaryFixture({ demo: true }));
    renderApp("/dashboard");
    expect(await screen.findByText(/Demo scope: synthetic sample records only/)).toBeInTheDocument();
  });

  it("shows an error state when the summary cannot load", async () => {
    server.use(http.get("/api/v1/reports/summary", () => errorBody("Internal server error.", 500)));
    renderApp("/dashboard");
    expect(await screen.findByText("Internal server error.")).toBeInTheDocument();
  });
});

describe("transaction analysis", () => {
  async function fillAndSubmit(amount: string, step: string, type = "TRANSFER") {
    await userEvent.type(await screen.findByLabelText("Amount"), amount);
    await userEvent.selectOptions(screen.getByLabelText("Transaction type"), type);
    await userEvent.type(screen.getByLabelText("Simulation step"), step);
    await userEvent.click(screen.getByRole("button", { name: "Score transaction" }));
  }

  it("ties the destination to the type, as in PaySim", () => {
    expect(destinationFor("PAYMENT")).toBe("merchant");
    expect(destinationFor("TRANSFER")).toBe("customer");
  });

  it("validates amount, step and identifier before sending", () => {
    const base = { externalId: "", amount: "100.00", type: "TRANSFER" as const, step: "5" };
    expect(validateForm(base)).toEqual({});
    expect(validateForm({ ...base, amount: "1.234" }).amount).toBeDefined();
    expect(validateForm({ ...base, amount: "0" }).amount).toBeDefined();
    expect(validateForm({ ...base, step: "1.5" }).step).toBeDefined();
    expect(validateForm({ ...base, step: "0" }).step).toBeDefined();
    expect(validateForm({ ...base, externalId: "=SUM(A1)" }).externalId).toBeDefined();
  });

  it("sends exactly the four inputs and shows the result with its explanation", async () => {
    let sent: Record<string, unknown> | null = null;
    server.use(
      http.post("/api/v1/transactions/predict", async ({ request }) => {
        sent = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(predictionFixture(), { status: 201 });
      }),
    );
    renderApp("/analyse");
    await fillAndSubmit("9000000", "5");
    const result = await screen.findByRole("article", { name: "Prediction result" });
    expect(sent).toEqual({ amount: "9000000", transaction_type: "TRANSFER", step: 5, destination_category: "customer" });
    expect(within(result).getByText("Flagged for review")).toBeInTheDocument();
    expect(within(result).getByText("0.8377")).toBeInTheDocument();
    expect(within(result).getByText(/not a percentage/)).toBeInTheDocument();
    expect(within(result).queryByText(/%/)).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "What moved this score" })).toBeInTheDocument();
    expect(screen.getByText(/does not establish/)).toBeInTheDocument();
  });

  it("sends merchant for PAYMENT", async () => {
    let sent: Record<string, unknown> | null = null;
    server.use(
      http.post("/api/v1/transactions/predict", async ({ request }) => {
        sent = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(predictionFixture(), { status: 201 });
      }),
    );
    renderApp("/analyse");
    await fillAndSubmit("10.50", "12", "PAYMENT");
    await screen.findByRole("article", { name: "Prediction result" });
    expect(sent).toMatchObject({ transaction_type: "PAYMENT", destination_category: "merchant" });
  });

  it("shows field errors without calling the API", async () => {
    let called = false;
    server.use(
      http.post("/api/v1/transactions/predict", () => {
        called = true;
        return HttpResponse.json(predictionFixture(), { status: 201 });
      }),
    );
    renderApp("/analyse");
    await fillAndSubmit("1.234", "0");
    expect(await screen.findByText(/at most two decimal places/)).toBeInTheDocument();
    expect(screen.getByText(/whole step/)).toBeInTheDocument();
    expect(called).toBe(false);
  });

  it("shows the API's message for a repeated identifier", async () => {
    server.use(
      http.post("/api/v1/transactions/predict", () => errorBody("A transaction with this identifier already exists.", 409)),
    );
    renderApp("/analyse");
    await fillAndSubmit("100", "5");
    expect(await screen.findByRole("alert")).toHaveTextContent("already exists");
  });

  it("is not offered to roles without the predict permission", async () => {
    server.use(
      http.get("/api/v1/auth/me", () =>
        HttpResponse.json({ id: "x", email: "x@example.com", role: "analyst", is_active: true, created_at: "2026-11-08T00:00:00Z", permissions: ["view_summary"], session_expires_at: null }),
      ),
    );
    renderApp("/analyse");
    expect(await screen.findByRole("heading", { name: "Not available for your role" })).toBeInTheDocument();
  });
});

describe("explainable AI", () => {
  it("shows saved importance with its limits, and explains a chosen prediction", async () => {
    server.use(
      http.get("/api/v1/models/feature-importance", () => HttpResponse.json(featureImportanceFixture())),
      http.get("/api/v1/transactions", () =>
        HttpResponse.json({ items: [summaryFixture().recent_activity[0]], total: 1, limit: 10, offset: 0 }),
      ),
      http.get("/api/v1/transactions/:id", () => HttpResponse.json({ ...predictionFixture(), batch_job_id: null, investigation: null })),
    );
    renderApp("/explainability");
    expect(await screen.findByRole("heading", { name: "Overall importance by input group" })).toBeInTheDocument();
    expect(screen.getByText("Type is TRANSFER")).toBeInTheDocument();
    expect(screen.getByText(/Fixture limitation/)).toBeInTheDocument();
    await userEvent.click(await screen.findByRole("button", { name: "Open" }));
    await waitFor(() => expect(screen.getByRole("heading", { name: "What moved this score" })).toBeInTheDocument());
  });

  it("says so when a prediction has no stored explanation", async () => {
    server.use(
      http.get("/api/v1/models/feature-importance", () => HttpResponse.json(featureImportanceFixture())),
      http.get("/api/v1/transactions", () =>
        HttpResponse.json({ items: [summaryFixture().recent_activity[0]], total: 1, limit: 10, offset: 0 }),
      ),
      http.get("/api/v1/transactions/:id", () =>
        HttpResponse.json({ ...predictionFixture(), explanation: null, batch_job_id: null, investigation: null }),
      ),
    );
    renderApp("/explainability");
    await userEvent.click(await screen.findByRole("button", { name: "Open" }));
    expect(await screen.findByText(/No explanation is stored for this transaction/)).toBeInTheDocument();
  });
});
