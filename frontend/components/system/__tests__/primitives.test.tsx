import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import HudLabel from "../HudLabel";
import Meter from "../Meter";
import SectionRule from "../SectionRule";
import SegmentedControl from "../SegmentedControl";
import Surface from "../Surface";

describe("Lumen primitives", () => {
  it("exposes meter values to assistive technology", () => {
    render(<Meter label="Attention" value={0.62} detail="Focus stability" />);
    expect(screen.getByRole("progressbar", { name: "Attention" })).toHaveAttribute("aria-valuenow", "62");
    expect(screen.getByText("Focus stability")).toBeInTheDocument();
  });

  it("reports segmented control changes", () => {
    const onChange = vi.fn();
    render(
      <SegmentedControl
        label="Quality"
        value="balanced"
        options={[
          { id: "cinematic", label: "Cinematic" },
          { id: "balanced", label: "Balanced" },
        ]}
        onChange={onChange}
      />,
    );
    expect(screen.getByRole("button", { name: "Balanced" })).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(screen.getByRole("button", { name: "Cinematic" }));
    expect(onChange).toHaveBeenCalledWith("cinematic");
  });

  it("renders labelled surfaces and section rules", () => {
    render(
      <Surface tone="rail" data-testid="rail">
        <HudLabel>Scene</HudLabel>
        <SectionRule label="Composition" />
      </Surface>,
    );
    expect(screen.getByTestId("rail")).toHaveClass("surface-rail");
    expect(screen.getByText("Composition")).toBeInTheDocument();
  });
});
