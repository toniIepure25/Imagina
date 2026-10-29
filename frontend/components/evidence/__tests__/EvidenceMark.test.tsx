import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { GlassBoxContext, type GlassBoxContextValue } from "../GlassBoxContext";
import EvidenceMark from "../EvidenceMark";

function value(overrides: Partial<GlassBoxContextValue> = {}): GlassBoxContextValue {
  return {
    enabled: true,
    preference: "on",
    activeEntry: null,
    setPreference: vi.fn(),
    openEvidence: vi.fn(),
    closeEvidence: vi.fn(),
    ...overrides,
  };
}

describe("EvidenceMark", () => {
  it("opens the drawer for a registered id", () => {
    const context = value();
    render(
      <GlassBoxContext.Provider value={context}>
        <EvidenceMark evidenceId="iqi.proxy" />
      </GlassBoxContext.Provider>,
    );
    const button = screen.getByRole("button", { name: /Evidence: IQI/i });
    fireEvent.click(button);
    expect(context.openEvidence).toHaveBeenCalledWith("iqi.proxy");
  });

  it("stays hidden when the glass box is off", () => {
    render(
      <GlassBoxContext.Provider value={value({ enabled: false })}>
        <EvidenceMark evidenceId="iqi.proxy" />
      </GlassBoxContext.Provider>,
    );
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("flags an unregistered id even when the glass box is off", () => {
    render(
      <GlassBoxContext.Provider value={value({ enabled: false })}>
        <EvidenceMark evidenceId="unknown.metric" />
      </GlassBoxContext.Provider>,
    );
    expect(screen.getByTitle("Unregistered evidence id: unknown.metric").textContent).toBe("?");
  });
});
