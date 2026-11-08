/**
 * A mock API for component tests, answering the real paths with fixtures.
 * Tests replace individual handlers with server.use(...) to simulate errors.
 */
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

import { metricsFixture, statusFixture, userFixture } from "./fixtures";

export const state = { role: "analyst" as "demo" | "analyst" | "investigator" | "admin", signedIn: true };

export function errorBody(detail: string, status: number, extra: Record<string, unknown> = {}) {
  return HttpResponse.json({ detail, request_id: "req-123", ...extra }, { status });
}

export const handlers = [
  http.get("/api/v1/auth/me", () =>
    state.signedIn ? HttpResponse.json(userFixture(state.role)) : errorBody("Could not validate credentials", 401),
  ),
  http.post("/api/v1/auth/session", async ({ request }) => {
    const body = (await request.json()) as { email: string; password: string };
    if (body.password !== "correct horse battery staple") {
      return errorBody("Incorrect email or password.", 401);
    }
    state.signedIn = true;
    return HttpResponse.json(userFixture(state.role));
  }),
  http.delete("/api/v1/auth/session", () => {
    state.signedIn = false;
    return new HttpResponse(null, { status: 204 });
  }),
  http.get("/api/v1/models/metrics", () => HttpResponse.json(metricsFixture())),
  http.get("/api/v1/system/status", () => HttpResponse.json(statusFixture())),
  http.get("/health", () => HttpResponse.json({ status: "ok" })),
  http.get("/api/v1/audit-logs", () =>
    HttpResponse.json({
      items: [
        {
          id: "22222222-2222-4222-8222-222222222222",
          user_id: null,
          action: "auth.login_failed",
          entity_type: "user",
          entity_id: null,
          details: null,
          created_at: "2026-11-08T09:00:00Z",
        },
      ],
      total: 1,
      limit: 20,
      offset: 0,
    }),
  ),
];

export const server = setupServer(...handlers);
