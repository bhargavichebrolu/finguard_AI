/**
 * Runs before every unit test file: DOM matchers, the mock API and a clean slate between tests.
 */
import "@testing-library/jest-dom/vitest";
import { cleanup, configure } from "@testing-library/react";
import { afterAll, afterEach, beforeAll } from "vitest";

import { server, state } from "./server";

// jsdom has no ResizeObserver, which Recharts' ResponsiveContainer needs. Browsers have one, and
// the Playwright tests check real chart rendering. Here charts get a zero size and tests read
// the table views instead.
class TestResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver ??= TestResizeObserver as unknown as typeof ResizeObserver;

// Pages load lazily. On a cold start, such as a fresh clone or CI, compiling a page's module the
// first time can take longer than Testing Library's default one-second wait, which made the first
// test in a file fail there and pass locally (found by the Phase 5 clean-clone check). Waiting
// longer changes no assertion: a test still fails if the expected content never appears.
configure({ asyncUtilTimeout: 5000 });

// Requests are sent to the page's own origin, as in the browser.
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));

afterEach(() => {
  cleanup();
  server.resetHandlers();
  state.role = "analyst";
  state.signedIn = true;
  document.cookie = "finguard_csrf=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/";
});

afterAll(() => server.close());
