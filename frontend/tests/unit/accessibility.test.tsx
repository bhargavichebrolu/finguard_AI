/**
 * Regression tests for the accessibility defects the M7 browser tests found: the confirmation
 * dialog let focus escape and did not return it, the mobile menu could not be closed with
 * Escape, and scrolling tables could not be reached by keyboard.
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it } from "vitest";

import { DataTable, TableScroll } from "../../src/components/DataTable";
import { ConfirmDialog } from "../../src/components/feedback";
import { renderApp } from "./render";
import { state } from "./server";

function DialogHarness() {
  const [open, setOpen] = useState(false);
  const [renders, setRenders] = useState(0);
  return (
    <>
      <button type="button" onClick={() => setOpen(true)}>
        Open dialog
      </button>
      <button type="button" onClick={() => setRenders((count) => count + 1)}>
        Outside {renders}
      </button>
      <ConfirmDialog
        open={open}
        title="Change this?"
        message="This is recorded."
        confirmLabel="Change it"
        onCancel={() => setOpen(false)}
        onConfirm={() => setOpen(false)}
      />
    </>
  );
}

describe("ConfirmDialog", () => {
  it("is named and described, and starts on Cancel", async () => {
    render(<DialogHarness />);
    await userEvent.click(screen.getByRole("button", { name: "Open dialog" }));
    const dialog = screen.getByRole("dialog", { name: "Change this?" });
    expect(dialog).toHaveAccessibleDescription("This is recorded.");
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(screen.getByRole("button", { name: "Cancel" })).toHaveFocus();
  });

  it("keeps Tab and Shift+Tab inside the dialog", async () => {
    render(<DialogHarness />);
    await userEvent.click(screen.getByRole("button", { name: "Open dialog" }));
    await userEvent.tab();
    expect(screen.getByRole("button", { name: "Change it" })).toHaveFocus();
    await userEvent.tab();
    expect(screen.getByRole("button", { name: "Cancel" })).toHaveFocus();
    await userEvent.tab({ shift: true });
    expect(screen.getByRole("button", { name: "Change it" })).toHaveFocus();
  });

  it("returns focus to the control that opened it, after Escape or a choice", async () => {
    render(<DialogHarness />);
    const opener = screen.getByRole("button", { name: "Open dialog" });
    await userEvent.click(opener);
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(opener).toHaveFocus();

    await userEvent.click(opener);
    await userEvent.click(screen.getByRole("button", { name: "Change it" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(opener).toHaveFocus();
  });
});

describe("TableScroll", () => {
  it("is a named group that keyboard users can focus to scroll", async () => {
    render(
      <TableScroll label="Wide table">
        <table>
          <tbody>
            <tr>
              <td>cell</td>
            </tr>
          </tbody>
        </table>
      </TableScroll>,
    );
    const area = screen.getByRole("group", { name: "Wide table, scrollable table" });
    await userEvent.tab();
    expect(area).toHaveFocus();
  });

  it("wraps every DataTable", () => {
    render(<DataTable caption="Rows" columns={[{ key: "a", header: "A", render: (row: { a: string }) => row.a }]} rows={[{ a: "x" }]} rowKey={(row) => row.a} emptyTitle="None" />);
    expect(screen.getByRole("group", { name: "Rows, scrollable table" })).toContainElement(screen.getByRole("table", { name: "Rows" }));
  });
});

describe("navigation on narrow screens", () => {
  it("closes the menu with Escape and returns focus to the menu button", async () => {
    state.role = "analyst";
    renderApp("/system");
    const menu = await screen.findByRole("button", { name: "Open navigation" });
    await userEvent.click(menu);
    expect(menu).toHaveAttribute("aria-expanded", "true");
    await userEvent.keyboard("{Escape}");
    expect(menu).toHaveAttribute("aria-expanded", "false");
    expect(menu).toHaveFocus();
  });

  it("keeps Sign out as the button's name when the label is hidden visually", async () => {
    state.role = "analyst";
    renderApp("/system");
    const signOut = await screen.findByRole("button", { name: "Sign out" });
    expect(signOut.querySelector(".sign-out-label")).toHaveTextContent("Sign out");
  });
});
