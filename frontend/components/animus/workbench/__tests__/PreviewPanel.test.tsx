import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { SceneDiff } from "@/lib/animusStudioApi";
import type { WorkbenchPreview } from "@/lib/workbenchState";
import { PreviewPanel } from "../PreviewBanner";

const preview = {
  kind: "version",
  version: {
    version_id: "version-2",
    number: 2,
    branch_id: "main",
    label: "Refined",
  },
} as unknown as WorkbenchPreview;

const diff: SceneDiff = {
  added: [{ entity_id: "new", label: "New tree", kind: "tree" }],
  removed: [{ entity_id: "gone", label: "Old tree", kind: "tree" }],
  changed: [
    {
      scope: "transform",
      entity_id: "moved",
      label: "Moved stone",
      path: "transform.position.x",
      before: 0,
      after: 2,
      provenance: "user_explicit",
    },
  ],
  locked_untouched: [],
  explanation: ["A short explanation."],
  warnings: [],
  before_hash: "a",
  after_hash: "b",
};

function renderPanel(overrides: Partial<React.ComponentProps<typeof PreviewPanel>> = {}) {
  return render(
    <PreviewPanel
      preview={preview}
      diff={diff}
      diffBasis="Since head"
      stale={false}
      busy={false}
      focusableIds={new Set(["moved", "new"])}
      onFocusEntity={() => {}}
      onKeep={() => {}}
      onDiscard={() => {}}
      onBranch={() => {}}
      onCompare={() => {}}
      {...overrides}
    />,
  );
}

describe("PreviewPanel", () => {
  it("states the comparison basis and focuses a changed entity", () => {
    const onFocusEntity = vi.fn();
    renderPanel({ onFocusEntity });
    expect(screen.getByTestId("diff-basis")).toHaveTextContent("Since head");
    fireEvent.click(screen.getByTestId("preview-change-row"));
    expect(onFocusEntity).toHaveBeenCalledWith("moved");
  });

  it("focuses an added entity", () => {
    const onFocusEntity = vi.fn();
    renderPanel({ onFocusEntity });
    fireEvent.click(screen.getByRole("button", { name: "Focus added New tree in the scene" }));
    expect(onFocusEntity).toHaveBeenCalledWith("new");
  });

  it("disables focus for a changed entity that is no longer in the preview", () => {
    renderPanel({ focusableIds: new Set(["new"]) });
    expect(screen.getByTestId("preview-change-row")).toBeDisabled();
    expect(screen.getByText("Not in scene")).toBeInTheDocument();
  });

  it("opens the comparison chamber from the preview", () => {
    const onCompare = vi.fn();
    renderPanel({ onCompare });
    fireEvent.click(screen.getByTestId("compare-preview-button"));
    expect(onCompare).toHaveBeenCalledTimes(1);
  });
});
