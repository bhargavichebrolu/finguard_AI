/** The API client: CSRF header, error normalisation and the session-ended signal. */
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { ApiError, CSRF_HEADER, createApiClient, onUnauthorized, readCookie, readCsrfToken, toApiError } from "../../src/services/api";
import { errorBody, server } from "./server";

function captureHeaders() {
  const seen: Record<string, string | null> = {};
  server.use(
    http.all("/api/v1/echo", ({ request }) => {
      seen[request.method] = request.headers.get(CSRF_HEADER);
      return HttpResponse.json({ ok: true });
    }),
  );
  return seen;
}

describe("api client", () => {
  it("sends the CSRF cookie as a header on requests that change data", async () => {
    document.cookie = "finguard_csrf=token-value; path=/";
    const seen = captureHeaders();
    const client = createApiClient("");
    await client.post("/api/v1/echo", {});
    await client.patch("/api/v1/echo", {});
    await client.delete("/api/v1/echo");
    await client.get("/api/v1/echo");
    expect(seen.POST).toBe("token-value");
    expect(seen.PATCH).toBe("token-value");
    expect(seen.DELETE).toBe("token-value");
    expect(seen.GET).toBeNull();
  });

  it("never reads or stores a token in browser storage", async () => {
    const setItem = vi.spyOn(Storage.prototype, "setItem");
    const getItem = vi.spyOn(Storage.prototype, "getItem");
    captureHeaders();
    await createApiClient("").post("/api/v1/echo", {});
    expect(setItem).not.toHaveBeenCalled();
    expect(getItem).not.toHaveBeenCalled();
  });

  it("turns error responses into ApiError with message, reference and field errors", async () => {
    server.use(
      http.post("/api/v1/echo", () =>
        errorBody("The request is not valid.", 422, {
          errors: [{ location: ["body", "amount"], message: "Input should be greater than 0", type: "x" }],
        }),
      ),
    );
    const error = await createApiClient("").post("/api/v1/echo", {}).catch((caught: unknown) => caught);
    expect(error).toBeInstanceOf(ApiError);
    const apiError = error as ApiError;
    expect(apiError.status).toBe(422);
    expect(apiError.message).toBe("The request is not valid.");
    expect(apiError.requestId).toBe("req-123");
    expect(apiError.fieldErrors).toEqual([{ location: "amount", message: "Input should be greater than 0" }]);
  });

  it("reads Retry-After on rate limits", async () => {
    server.use(
      http.get("/api/v1/echo", () =>
        HttpResponse.json({ detail: "Too many requests." }, { status: 429, headers: { "Retry-After": "42" } }),
      ),
    );
    const error = (await createApiClient("").get("/api/v1/echo").catch((caught: unknown) => caught)) as ApiError;
    expect(error.retryAfterSeconds).toBe(42);
  });

  it("reports a network failure in plain words", () => {
    expect(toApiError(new Error("socket hang up")).status).toBe(0);
    expect(toApiError(new Error("socket hang up")).message).toContain("could not be reached");
  });

  it("signals a session ending on 401, except for a failed sign-in", async () => {
    const handler = vi.fn();
    onUnauthorized(handler);
    server.use(
      http.get("/api/v1/echo", () => errorBody("Could not validate credentials", 401)),
      http.post("/api/v1/auth/session", () => errorBody("Incorrect email or password.", 401)),
    );
    const client = createApiClient("");
    await client.post("/api/v1/auth/session", {}).catch(() => undefined);
    expect(handler).not.toHaveBeenCalled();
    await client.get("/api/v1/echo").catch(() => undefined);
    expect(handler).toHaveBeenCalledTimes(1);
    onUnauthorized(null);
  });

  it("reads cookies by exact name", () => {
    document.cookie = "other_finguard_csrf=wrong; path=/";
    document.cookie = "finguard_csrf=right; path=/";
    expect(readCookie("finguard_csrf")).toBe("right");
    expect(readCookie("missing")).toBeNull();
  });

  it("prefers the __Host- CSRF cookie that Secure production cookies use", () => {
    // jsdom will not store a __Host- cookie on an insecure test origin, so the browser's cookie
    // string is supplied directly.
    const cookie = vi.spyOn(document, "cookie", "get");
    cookie.mockReturnValue("finguard_csrf=plain; __Host-finguard_csrf=prefixed");
    expect(readCsrfToken()).toBe("prefixed");
    cookie.mockReturnValue("finguard_csrf=plain");
    expect(readCsrfToken()).toBe("plain");
    cookie.mockReturnValue("");
    expect(readCsrfToken()).toBeNull();
    cookie.mockRestore();
  });
});
