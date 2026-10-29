import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { useRef, useState } from "react";
import { describe, expect, it } from "vitest";
import { useFocusTrap } from "../useFocusTrap";

function Dialog() {
  const [open, setOpen] = useState(false);
  const dialogRef = useRef<HTMLDivElement>(null);
  useFocusTrap(open, dialogRef);
  return (
    <div>
      <button type="button" onClick={() => setOpen(true)}>
        Open
      </button>
      <button type="button" onClick={() => setOpen(false)}>
        Close outside
      </button>
      {open ? (
        <div ref={dialogRef} role="dialog" aria-label="Test dialog">
          <button type="button">First</button>
          <button type="button">Last</button>
          <button type="button" onClick={() => setOpen(false)}>
            Dismiss
          </button>
        </div>
      ) : null}
    </div>
  );
}

describe("useFocusTrap", () => {
  it("focuses the first control, cycles Tab, and restores the trigger", () => {
    render(<Dialog />);
    const trigger = screen.getByRole("button", { name: "Open" });
    trigger.focus();
    fireEvent.click(trigger);
    expect(screen.getByRole("button", { name: "First" })).toHaveFocus();

    const last = screen.getByRole("button", { name: "Dismiss" });
    last.focus();
    fireEvent.keyDown(document, { key: "Tab" });
    expect(screen.getByRole("button", { name: "First" })).toHaveFocus();

    fireEvent.keyDown(document, { key: "Tab", shiftKey: true });
    expect(last).toHaveFocus();

    fireEvent.click(last);
    expect(trigger).toHaveFocus();
  });
});
