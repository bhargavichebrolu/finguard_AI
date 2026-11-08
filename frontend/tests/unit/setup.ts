/**
 * Runs before every unit test file: DOM matchers, the mock API and a clean slate between tests.
 */
import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterAll, afterEach, beforeAll } from "vitest";

import { server, state } from "./server";

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
