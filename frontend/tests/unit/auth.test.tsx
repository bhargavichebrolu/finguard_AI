/** Sign-in, session restore, sign-out, session expiry and role-based navigation. */
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { renderApp } from "./render";
import { errorBody, server, state } from "./server";

describe("authentication", () => {
  it("restores a session from the cookie on load", async () => {
    renderApp("/system");
    expect(await screen.findByRole("heading", { name: "System Information" })).toBeInTheDocument();
    expect(screen.getByText("analyst@example.com")).toBeInTheDocument();
  });

  it("sends a signed-out visitor to the login page", async () => {
    state.signedIn = false;
    renderApp("/system");
    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
  });

  it("signs in and returns to the page that was asked for", async () => {
    state.signedIn = false;
    renderApp("/system");
    await userEvent.type(await screen.findByLabelText("Email"), "analyst@example.com");
    await userEvent.type(screen.getByLabelText("Password"), "correct horse battery staple");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("heading", { name: "System Information" })).toBeInTheDocument();
  });

  it("shows the API's message for wrong credentials", async () => {
    state.signedIn = false;
    renderApp("/login");
    await userEvent.type(await screen.findByLabelText("Email"), "analyst@example.com");
    await userEvent.type(screen.getByLabelText("Password"), "wrong password");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Incorrect email or password.");
  });

  it("explains a rate limit with the waiting time", async () => {
    state.signedIn = false;
    server.use(
      http.post("/api/v1/auth/session", () =>
        HttpResponse.json({ detail: "Too many requests." }, { status: 429, headers: { "Retry-After": "30" } }),
      ),
    );
    renderApp("/login");
    await userEvent.type(await screen.findByLabelText("Email"), "a@example.com");
    await userEvent.type(screen.getByLabelText("Password"), "anything");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Try again in 30 seconds");
  });

  it("signs out through the API and returns to login", async () => {
    renderApp("/system");
    await userEvent.click(await screen.findByRole("button", { name: "Sign out" }));
    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("You have signed out.");
    expect(state.signedIn).toBe(false);
  });

  it("returns to login with a message when the API ends the session", async () => {
    renderApp("/system");
    await screen.findByRole("heading", { name: "System Information" });
    server.use(http.get("/api/v1/audit-logs", () => errorBody("Could not validate credentials", 401)));
    state.role = "admin";
    server.use(http.get("/api/v1/system/status", () => errorBody("Could not validate credentials", 401)));
    renderApp("/system");
    await waitFor(() => expect(screen.getAllByRole("heading", { name: "Sign in" }).length).toBeGreaterThan(0));
  });
});

describe("navigation and permissions", () => {
  it("shows the demo banner only to demo users", async () => {
    state.role = "demo";
    renderApp("/system");
    expect(await screen.findByText(/Demo mode: everything you create here/)).toBeInTheDocument();
  });

  it("does not show the demo banner to other roles", async () => {
    renderApp("/system");
    await screen.findByRole("heading", { name: "System Information" });
    expect(screen.queryByText(/Demo mode/)).not.toBeInTheDocument();
  });

  it("shows the audit log only to administrators", async () => {
    renderApp("/system");
    await screen.findByText("Frozen model");
    expect(screen.queryByRole("heading", { name: "Audit log" })).not.toBeInTheDocument();
    state.role = "admin";
    renderApp("/system");
    expect(await screen.findByRole("heading", { name: "Audit log" })).toBeInTheDocument();
  });

  it("lists navigation entries and marks the current page", async () => {
    renderApp("/system");
    const nav = await screen.findByRole("navigation", { name: "Main navigation" });
    const link = within(nav).getByRole("link", { name: /System Information/ });
    expect(link).toHaveClass("active");
  });

  it("collapses and expands the navigation", async () => {
    renderApp("/system");
    const toggle = await screen.findByRole("button", { name: "Collapse navigation" });
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    await userEvent.click(toggle);
    expect(screen.getByRole("button", { name: "Expand navigation" })).toHaveAttribute("aria-expanded", "false");
  });

  it("shows a not-found page for an unknown address", async () => {
    renderApp("/no-such-page");
    expect(await screen.findByRole("heading", { name: "Page not found" })).toBeInTheDocument();
  });
});
