/** Formatting rules, the score disclosure, shared states and the System Information page. */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http } from "msw";
import { describe, expect, it, vi } from "vitest";

import { ConfirmDialog, ErrorState } from "../../src/components/feedback";
import { ScoreDisclosure } from "../../src/components/ScoreDisclosure";
import { ModelLimitsProvider } from "../../src/hooks/useModelLimits";
import { ApiError } from "../../src/services/api";
import {
  describeDecision,
  formatRate,
  formatRiskScore,
  formatScore,
  humanise,
} from "../../src/utils/format";
import { TEST_NOTE_FPR, TEST_NOTE_RECALL } from "./fixtures";
import { renderApp } from "./render";
import { errorBody, server } from "./server";

describe("formatting", () => {
  it("writes model scores as plain numbers, never as percentages", () => {
    expect(formatScore(0.8377037048339844)).toBe("0.8377");
    expect(formatScore(0.0284)).not.toContain("%");
    expect(formatScore(null)).toBe("–");
  });

  it("labels the risk score as not a percentage", () => {
    expect(formatRiskScore(83.77)).toBe("83.8 (score × 100, not a percentage)");
  });

  it("writes measured rates as percentages", () => {
    expect(formatRate(0.4586)).toBe("45.9%");
    expect(formatRate(0.00282, 3)).toBe("0.282%");
  });

  it("describes decisions without claiming fraud", () => {
    expect(describeDecision("FLAG_FOR_REVIEW")).toBe("Flagged for review");
    expect(describeDecision("NOT_FLAGGED")).toBe("Not flagged");
    expect(humanise("UNDER_REVIEW")).toBe("Under review");
  });
});

describe("score disclosure", () => {
  it("states what a score is and shows the API's measured limitations", async () => {
    render(
      <ModelLimitsProvider>
        <ScoreDisclosure />
      </ModelLimitsProvider>,
    );
    expect(screen.getByText(/not calibrated and are not the chance/)).toBeInTheDocument();
    expect(await screen.findByText(TEST_NOTE_FPR)).toBeInTheDocument();
    expect(screen.getByText(TEST_NOTE_RECALL)).toBeInTheDocument();
  });

  it("warns when the limitations cannot be loaded", async () => {
    server.use(http.get("/api/v1/models/metrics", () => errorBody("Internal server error.", 500)));
    render(
      <ModelLimitsProvider>
        <ScoreDisclosure />
      </ModelLimitsProvider>,
    );
    expect(await screen.findByRole("alert")).toHaveTextContent("could not be loaded");
  });
});

describe("shared states", () => {
  it("shows an error with its reference and a retry", async () => {
    const retry = vi.fn();
    render(<ErrorState error={new ApiError("Not found.", 404, "req-9")} onRetry={retry} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Not found.");
    expect(screen.getByText("Reference: req-9")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(retry).toHaveBeenCalled();
  });

  it("asks before acting and backs out on Escape", async () => {
    const confirm = vi.fn();
    const cancel = vi.fn();
    render(
      <ConfirmDialog open title="Close case?" message="Sure?" confirmLabel="Close case" onConfirm={confirm} onCancel={cancel} />,
    );
    expect(screen.getByRole("dialog", { name: "Close case?" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cancel" })).toHaveFocus();
    await userEvent.keyboard("{Escape}");
    expect(cancel).toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: "Close case" }));
    expect(confirm).toHaveBeenCalled();
  });
});

describe("system information page", () => {
  it("shows live service and frozen model details", async () => {
    renderApp("/system");
    expect(await screen.findByText("Available")).toBeInTheDocument();
    expect(screen.getByText("fraud_detector_v1")).toBeInTheDocument();
    expect(screen.getByText("a".repeat(64))).toBeInTheDocument();
    expect(screen.getByText(/frozen; cannot be changed here/)).toBeInTheDocument();
  });

  it("shows an error state when the status cannot load", async () => {
    server.use(http.get("/api/v1/system/status", () => errorBody("Internal server error.", 500)));
    renderApp("/system");
    expect(await screen.findByText("Internal server error.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
  });
});
