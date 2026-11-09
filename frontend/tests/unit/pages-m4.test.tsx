/** CSV Batch Analysis and the Transaction Explorer, against the mock API. */
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { checkFile } from "../../src/pages/BatchAnalysisPage";
import { EMPTY_FILTERS, toQuery } from "../../src/pages/TransactionExplorerPage";
import { batchFixture, predictionFixture, settingsFixture, summaryFixture } from "./fixtures";
import { renderApp } from "./render";
import { errorBody, server } from "./server";

const ROW = summaryFixture().recent_activity[0];

function page(items: unknown[], total = items.length) {
  return { items, total, limit: 25, offset: 0 };
}

function csv(name: string, text: string) {
  return new File([text], name, { type: "text/csv" });
}

beforeEach(() => {
  URL.createObjectURL = vi.fn(() => "blob:fixture");
  URL.revokeObjectURL = vi.fn();
  server.use(
    http.get("/api/v1/settings", () => HttpResponse.json(settingsFixture())),
    http.get("/api/v1/batches", () => HttpResponse.json(page([]))),
  );
});

afterEach(() => vi.restoreAllMocks());

describe("batch analysis", () => {
  it("checks type, emptiness and size against the API's limit", () => {
    expect(checkFile(csv("data.txt", "x"), 1000)).toMatch(/\.csv/);
    expect(checkFile(csv("data.csv", ""), 1000)).toMatch(/empty/);
    expect(checkFile(csv("data.csv", "x".repeat(1001)), 1000)).toMatch(/larger/);
    expect(checkFile(csv("DATA.CSV", "a,b"), 1000)).toBeNull();
  });

  it("refuses an oversized file without uploading it", async () => {
    let uploaded = false;
    server.use(
      http.post("/api/v1/batches/upload", () => {
        uploaded = true;
        return HttpResponse.json(batchFixture(), { status: 202 });
      }),
    );
    renderApp("/batches");
    await screen.findByText(/Up to 1,000 bytes/);
    await userEvent.upload(screen.getByLabelText("CSV file"), csv("big.csv", "x".repeat(2000)));
    expect(screen.getByRole("alert")).toHaveTextContent("larger than the 1,000 byte limit");
    expect(screen.getByRole("button", { name: "Upload and score" })).toBeDisabled();
    expect(uploaded).toBe(false);
  });

  it("checks a file chosen before the upload limits have loaded", async () => {
    // Regression found by the browser tests: the check used to run only when the file was
    // chosen, so a file picked before the limits arrived was never checked.
    let release: () => void = () => undefined;
    const limitsHeld = new Promise<void>((resolve) => {
      release = resolve;
    });
    server.use(
      http.get("/api/v1/settings", async () => {
        await limitsHeld;
        return HttpResponse.json(settingsFixture());
      }),
    );
    renderApp("/batches");
    await userEvent.upload(await screen.findByLabelText("CSV file"), csv("big.csv", "x".repeat(2000)));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    release();
    expect(await screen.findByRole("alert")).toHaveTextContent("larger than the 1,000 byte limit");
    expect(screen.getByRole("button", { name: "Upload and score" })).toBeDisabled();
  });

  it("says a job is resuming after an interruption, and keeps progress through a lost poll", async () => {
    let polls = 0;
    server.use(
      http.get("/api/v1/batches", () => HttpResponse.json(page([batchFixture({ status: "PROCESSING", attempts: 2 })]))),
      http.get("/api/v1/batches/:id", () => {
        polls += 1;
        if (polls === 2) return errorBody("Bad gateway", 502);
        if (polls < 4) return HttpResponse.json(batchFixture({ status: "PROCESSING", attempts: 2, processed_records: 1 }));
        return HttpResponse.json(batchFixture({ attempts: 2 }));
      }),
      http.get("/api/v1/batches/:id/results", () => HttpResponse.json(page([ROW]))),
    );
    renderApp("/batches");
    const recent = await screen.findByRole("table", { name: "Recent batch uploads" });
    await userEvent.click(within(recent).getByRole("button", { name: "Open" }));
    const status = await screen.findByRole("article", { name: "Batch status" });
    expect(await within(status).findByText(/Resuming after an interruption: 1 of 3 rows/)).toBeInTheDocument();
    expect(await within(status).findByText(/Lost contact with the server/, {}, { timeout: 3000 })).toBeInTheDocument();
    expect(within(status).getByText(/Resuming after an interruption: 1 of 3 rows/)).toBeInTheDocument();
    expect(await within(status).findByText(/Completed with errors: 3 of 3 rows/, {}, { timeout: 5000 })).toBeInTheDocument();
  });

  it("uploads, follows processing to the end, and shows counts, ignored columns and results", async () => {
    let polls = 0;
    server.use(
      http.post("/api/v1/batches/upload", () =>
        HttpResponse.json(batchFixture({ status: "PENDING", processed_records: 0, progress_percent: 0 }), {
          status: 202,
        }),
      ),
      http.get("/api/v1/batches/:id", () => {
        polls += 1;
        const running = batchFixture({ status: "PROCESSING", processed_records: 1, progress_percent: 33.3 });
        return HttpResponse.json(polls === 1 ? running : batchFixture());
      }),
      http.get("/api/v1/batches/:id/results", () => HttpResponse.json(page([ROW]))),
    );
    renderApp("/batches");
    await screen.findByText(/Up to 1,000 bytes/);
    const text = "amount,transaction_type,step,destination_category\n1,TRANSFER,1,customer\n";
    await userEvent.upload(screen.getByLabelText("CSV file"), csv("upload.csv", text));
    await userEvent.click(screen.getByRole("button", { name: "Upload and score" }));
    const status = await screen.findByRole("article", { name: "Batch status" });
    expect(await within(status).findByText(/Processing: 1 of 3 rows/)).toBeInTheDocument();
    expect(
      await within(status).findByText(/Completed with errors: 3 of 3 rows/, {}, { timeout: 3000 }),
    ).toBeInTheDocument();
    expect(within(status).getByText("isFraud: kept out of scoring")).toBeInTheDocument();
    expect(within(status).getByText(/stored separately and never used to score/)).toBeInTheDocument();
    expect(await screen.findByText("FIX-1")).toBeInTheDocument();
    expect(within(status).getByRole("button", { name: "Download error report" })).toBeInTheDocument();
  });

  it("downloads the error report through the signed-in client", async () => {
    let requested = false;
    server.use(
      http.get("/api/v1/batches", () => HttpResponse.json(page([batchFixture()]))),
      http.get("/api/v1/batches/:id", () => HttpResponse.json(batchFixture())),
      http.get("/api/v1/batches/:id/results", () => HttpResponse.json(page([]))),
      http.get("/api/v1/batches/:id/errors", () => {
        requested = true;
        return new HttpResponse("row_number,column,message\n4,amount,Invalid\n", {
          headers: { "Content-Type": "text/csv", "Content-Disposition": 'attachment; filename="batch-errors.csv"' },
        });
      }),
    );
    renderApp("/batches");
    await userEvent.click(await screen.findByRole("button", { name: "Open" }));
    await userEvent.click(await screen.findByRole("button", { name: "Download error report" }));
    await waitFor(() => expect(requested).toBe(true));
    await waitFor(() => expect(URL.createObjectURL).toHaveBeenCalled());
  });

  it("shows the API's refusal of a bad file", async () => {
    server.use(http.post("/api/v1/batches/upload", () => errorBody("Missing required columns: ['step']", 422)));
    renderApp("/batches");
    await screen.findByText(/Up to 1,000 bytes/);
    await userEvent.upload(screen.getByLabelText("CSV file"), csv("bad.csv", "amount\n1\n"));
    await userEvent.click(screen.getByRole("button", { name: "Upload and score" }));
    expect(await screen.findByText("Missing required columns: ['step']")).toBeInTheDocument();
  });

  it("shows a failed job's message", async () => {
    const failed = batchFixture({
      status: "FAILED",
      error_message: "The server restarted during processing. Upload the file again.",
    });
    server.use(
      http.get("/api/v1/batches", () => HttpResponse.json(page([failed]))),
      http.get("/api/v1/batches/:id", () => HttpResponse.json(failed)),
      http.get("/api/v1/batches/:id/results", () => HttpResponse.json(page([]))),
    );
    renderApp("/batches");
    await userEvent.click(await screen.findByRole("button", { name: "Open" }));
    expect(await screen.findByText(/Upload the file again/)).toBeInTheDocument();
  });
});

describe("transaction explorer", () => {
  it("turns filters into API parameters and leaves blanks out", () => {
    expect(toQuery(EMPTY_FILTERS, 0)).toEqual({ sort_by: "created_at", sort_order: "desc", limit: 25, offset: 0 });
    const filters = {
      ...EMPTY_FILTERS,
      externalId: " FIX ",
      riskLevel: "HIGH",
      amountMin: "10",
      stepMax: "24",
      investigationStatus: "NEW",
    };
    expect(toQuery(filters, 25)).toMatchObject({
      external_id: "FIX",
      risk_level: "HIGH",
      amount_min: "10",
      step_max: "24",
      investigation_status: "NEW",
      offset: 25,
    });
  });

  it("sends the chosen filters to the API and shows matching rows", async () => {
    const urls: URL[] = [];
    server.use(
      http.get("/api/v1/transactions", ({ request }) => {
        urls.push(new URL(request.url));
        return HttpResponse.json(page([ROW]));
      }),
    );
    renderApp("/transactions");
    expect(await screen.findByText("FIX-1")).toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText("Risk level"), "HIGH");
    await userEvent.selectOptions(screen.getByLabelText("Decision"), "FLAG_FOR_REVIEW");
    await userEvent.type(screen.getByLabelText("Step from"), "1");
    await userEvent.selectOptions(screen.getByLabelText("Sort by"), "model_score");
    await userEvent.click(screen.getByRole("button", { name: "Apply filters" }));
    await waitFor(() => expect(urls.length).toBe(2));
    const params = urls[1].searchParams;
    expect(params.get("risk_level")).toBe("HIGH");
    expect(params.get("prediction")).toBe("FLAG_FOR_REVIEW");
    expect(params.get("step_min")).toBe("1");
    expect(params.get("sort_by")).toBe("model_score");
    expect(params.has("amount_min")).toBe(false);
  });

  it("pages through results", async () => {
    const offsets: string[] = [];
    server.use(
      http.get("/api/v1/transactions", ({ request }) => {
        const offset = new URL(request.url).searchParams.get("offset") ?? "";
        offsets.push(offset);
        return HttpResponse.json({ items: [ROW], total: 60, limit: 25, offset: Number(offset) });
      }),
    );
    renderApp("/transactions");
    await screen.findByText("1–25 of 60");
    await userEvent.click(screen.getByRole("button", { name: "Next page" }));
    await waitFor(() => expect(offsets).toContain("25"));
    expect(await screen.findByText("26–50 of 60")).toBeInTheDocument();
  });

  it("shows an empty state when nothing matches", async () => {
    server.use(http.get("/api/v1/transactions", () => HttpResponse.json(page([]))));
    renderApp("/transactions");
    expect(await screen.findByText("No transactions match")).toBeInTheDocument();
  });

  it("opens the full detail with investigation history, notes and explanation", async () => {
    const investigation = {
      id: "55555555-5555-4555-8555-555555555555",
      prediction_id: "44444444-4444-4444-8444-444444444444",
      status: "UNDER_REVIEW",
      assigned_user_id: null,
      created_at: "2026-11-08T10:00:00Z",
      updated_at: "2026-11-08T11:00:00Z",
      notes: [{ id: "n1", user_id: null, note: "Fixture note text.", created_at: "2026-11-08T11:00:00Z" }],
      history: [
        { from_status: null, to_status: "NEW", changed_by: null, created_at: "2026-11-08T10:00:00Z" },
        { from_status: "NEW", to_status: "UNDER_REVIEW", changed_by: null, created_at: "2026-11-08T11:00:00Z" },
      ],
    };
    server.use(
      http.get("/api/v1/transactions", () => HttpResponse.json(page([ROW]))),
      http.get("/api/v1/transactions/:id", () =>
        HttpResponse.json({ ...predictionFixture(), batch_job_id: null, investigation }),
      ),
    );
    renderApp("/transactions");
    await userEvent.click(await screen.findByRole("button", { name: "Open" }));
    const detail = await screen.findByRole("region", { name: "Transaction detail" });
    expect(within(detail).getByText("Fixture note text.")).toBeInTheDocument();
    expect(within(detail).getByText(/New to Under review/)).toBeInTheDocument();
    expect(within(detail).getByText(/Workflow label, not a verified finding/)).toBeInTheDocument();
    expect(within(detail).getByRole("heading", { name: "What moved this score" })).toBeInTheDocument();
    expect(within(detail).getByRole("link", { name: "Open in the Investigation Centre" })).toHaveAttribute(
      "href",
      `/investigations?open=${investigation.id}`,
    );
    await userEvent.click(within(detail).getByRole("button", { name: "Close" }));
    expect(screen.queryByRole("region", { name: "Transaction detail" })).not.toBeInTheDocument();
  });
});
