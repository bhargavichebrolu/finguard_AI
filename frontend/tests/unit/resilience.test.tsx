/**
 * Phase 5 M7: what the interface does when the API is slow, unavailable or failing, and when a
 * page's code cannot be downloaded.
 */
import { render, screen } from "@testing-library/react";
import { AxiosError, AxiosHeaders } from "axios";
import userEvent from "@testing-library/user-event";
import { delay, http, HttpResponse } from "msw";
import { lazy, Suspense } from "react";
import { describe, expect, it, vi } from "vitest";

import { ErrorBoundary, isDownloadFailure } from "../../src/components/ErrorBoundary";
import {
  ApiError,
  MAY_HAVE_SAVED,
  TIMEOUT_MESSAGE,
  UNREACHABLE_MESSAGE,
  createApiClient,
  toApiError,
} from "../../src/services/api";
import { renderApp } from "./render";
import { errorBody, server } from "./server";

async function failure(request: Promise<unknown>): Promise<ApiError> {
  return (await request.catch((caught: unknown) => caught)) as ApiError;
}

describe("api client when the server does not answer", () => {
  it("says a slow request timed out, not that the server is unreachable", () => {
    // What axios raises when its timeout passes. (The mock server's interception in jsdom does
    // not enforce XHR timeouts, so the error is built as axios documents it.)
    const timedOut = (method: string) =>
      new AxiosError("timeout of 30000ms exceeded", AxiosError.ECONNABORTED, {
        method,
        url: "/api/v1/transactions/predict",
        headers: new AxiosHeaders(),
      });
    expect(toApiError(timedOut("get")).status).toBe(0);
    expect(toApiError(timedOut("get")).message).toBe(TIMEOUT_MESSAGE);
    expect(toApiError(timedOut("post")).message).toBe(TIMEOUT_MESSAGE + MAY_HAVE_SAVED);
  });

  it("keeps a slow answer that arrives within the timeout", async () => {
    server.use(http.get("/api/v1/slow", async () => {
      await delay(300);
      return HttpResponse.json({ ok: true });
    }));
    expect((await createApiClient("").get("/api/v1/slow")).data).toEqual({ ok: true });
  });

  it("warns that a change with no answer may still have been saved", async () => {
    server.use(http.post("/api/v1/transactions/predict", () => HttpResponse.error()));
    const error = await failure(createApiClient("").post("/api/v1/transactions/predict", {}));
    expect(error.message).toBe(UNREACHABLE_MESSAGE + MAY_HAVE_SAVED);
  });

  it("gives a read with no answer no such warning, nor a failed sign-in", async () => {
    server.use(
      http.get("/api/v1/transactions", () => HttpResponse.error()),
      http.post("/api/v1/auth/session", () => HttpResponse.error()),
    );
    expect((await failure(createApiClient("").get("/api/v1/transactions"))).message).toBe(UNREACHABLE_MESSAGE);
    expect((await failure(createApiClient("").post("/api/v1/auth/session", {}))).message).toBe(UNREACHABLE_MESSAGE);
  });

  it("shows the API's own message for a database outage, with its reference", async () => {
    server.use(http.get("/api/v1/transactions", () => errorBody("The database could not be reached. Try again in a moment.", 503)));
    const error = await failure(createApiClient("").get("/api/v1/transactions"));
    expect([error.status, error.message, error.requestId]).toEqual([503, "The database could not be reached. Try again in a moment.", "req-123"]);
  });

  it("explains a proxy's bad-gateway answer as the server being unavailable", async () => {
    server.use(http.get("/api/v1/transactions", () => new HttpResponse("<html>Bad Gateway</html>", { status: 502 })));
    const error = await failure(createApiClient("").get("/api/v1/transactions"));
    expect(error.message).toBe("The server is unavailable at the moment. Try again shortly.");
    expect(error.message).not.toContain("html");
  });
});

describe("starting while the server is unavailable", () => {
  it("does not send a signed-in user to the sign-in page, and recovers on Try again", async () => {
    server.use(http.get("/api/v1/auth/me", () => errorBody("The database could not be reached. Try again in a moment.", 503)));
    renderApp("/system");
    expect(await screen.findByRole("heading", { name: "FinGuard AI is unavailable" })).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("The database could not be reached");
    expect(screen.getByText("Reference: req-123")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Sign in" })).not.toBeInTheDocument();

    server.resetHandlers(); // the server is back, and the session cookie was never lost
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByRole("heading", { name: "System Information" })).toBeInTheDocument();
  });

  it("treats no answer at all the same way", async () => {
    server.use(http.get("/api/v1/auth/me", () => HttpResponse.error()));
    renderApp("/dashboard");
    expect(await screen.findByRole("heading", { name: "FinGuard AI is unavailable" })).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent(UNREACHABLE_MESSAGE);
  });
});

describe("a page that fails while it is shown", () => {
  function Throws({ error }: { error: Error }): never {
    throw error;
  }

  it("offers a reload when a page's code could not be downloaded", async () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    const Missing = lazy(() => Promise.reject(new TypeError("Failed to fetch dynamically imported module: http://x/assets/Page-1.js")));
    const reload = vi.fn();
    render(
      <ErrorBoundary reload={reload}>
        <Suspense fallback={null}>
          <Missing />
        </Suspense>
      </ErrorBoundary>,
    );
    expect(await screen.findByRole("heading", { name: "This page could not be loaded" })).toBeInTheDocument();
    expect(screen.getByRole("alert")).not.toHaveTextContent("assets/Page-1.js");
    await userEvent.click(screen.getByRole("button", { name: "Reload" }));
    expect(reload).toHaveBeenCalledOnce();
  });

  it("gives any other error a general message without its text", () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    render(
      <ErrorBoundary reload={vi.fn()}>
        <Throws error={new Error("secret internal detail")} />
      </ErrorBoundary>,
    );
    expect(screen.getByRole("heading", { name: "Something went wrong on this page" })).toBeInTheDocument();
    expect(screen.getByRole("alert")).not.toHaveTextContent("secret internal detail");
  });

  it("recognises how each browser reports a failed page download", () => {
    expect(isDownloadFailure(new TypeError("Failed to fetch dynamically imported module: http://x/a.js"))).toBe(true); // Chromium
    expect(isDownloadFailure(new TypeError("error loading dynamically imported module: http://x/a.js"))).toBe(true); // Firefox
    expect(isDownloadFailure(new TypeError("Importing a module script failed."))).toBe(true); // WebKit
    expect(isDownloadFailure(new Error("Cannot read properties of undefined"))).toBe(false);
  });
});
