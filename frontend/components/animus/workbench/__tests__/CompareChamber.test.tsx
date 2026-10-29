import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { SceneGraph } from "@/lib/animusStudioApi";
import type { SceneComparison } from "@/lib/sceneCompare";
import CompareChamber from "../CompareChamber";

vi.mock("@/components/animus/AnimusScene", () => ({
  default: (props: {
    scene: { version: number };
    visibleIds: Set<string> | null;
    diff?: unknown;
    traceScene?: unknown;
  }) => (
    <div
      data-testid={`compare-scene-${props.scene.version}`}
      data-visible={props.visibleIds ? [...props.visibleIds].join(",") : "all"}
      data-diff={props.diff ? "yes" : "no"}
      data-trace={props.traceScene ? "yes" : "no"}
    />
  ),
}));

function scene(version: number): SceneGraph {
  return {
    version,
    camera: { position: [0, 4, 12], target: [0, 1, 0], fov: 45 },
  } as SceneGraph;
}

const diff: SceneComparison = {
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
};

function renderChamber(overrides: Partial<React.ComponentProps<typeof CompareChamber>> = {}) {
  return render(
    <CompareChamber
      head={scene(3)}
      preview={scene(2)}
      diff={diff}
      headLabel="v3 · Main"
      previewLabel="v2"
      basis="Since head"
      onClose={() => {}}
      {...overrides}
    />,
  );
}

describe("CompareChamber", () => {
  it("labels both sides, states the basis, and reports counts", () => {
    renderChamber();
    expect(screen.getByTestId("compare-chamber")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Head and preview, one camera" })).toBeInTheDocument();
    expect(screen.getByText("v3 · Main")).toBeInTheDocument();
    expect(screen.getByText("v2")).toBeInTheDocument();
    expect(screen.getByTestId("compare-basis")).toHaveTextContent(
      "Since head · +1 added · ~1 changed · −1 removed",
    );
    expect(screen.getByTestId("compare-scene-3")).toHaveAttribute("data-visible", "all");
    expect(screen.getByTestId("compare-scene-2")).toHaveAttribute("data-visible", "all");
    expect(screen.getByTestId("compare-scene-2")).toHaveAttribute("data-diff", "yes");
    expect(screen.getByTestId("compare-scene-2")).toHaveAttribute("data-trace", "yes");
  });

  it("filters unchanged entities on each side when Only differences is on", () => {
    renderChamber();
    fireEvent.click(screen.getByRole("checkbox", { name: "Only differences" }));
    expect(screen.getByTestId("compare-scene-3")).toHaveAttribute("data-visible", "moved,gone");
    expect(screen.getByTestId("compare-scene-2")).toHaveAttribute("data-visible", "moved,new");
  });

  it("reports no differences and disables the filter", () => {
    renderChamber({
      diff: { added: [], removed: [], changed: [], locked_untouched: [] },
    });
    expect(screen.getByText("No differences between head and preview.")).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: "Only differences" })).toBeDisabled();
  });

  it("keeps context visible when only scene-level changes exist", () => {
    renderChamber({
      diff: {
        added: [],
        removed: [],
        changed: [
          {
            scope: "scene",
            entity_id: null,
            label: "Scene",
            path: "atmosphere.sky.top",
            before: "#000000",
            after: "#5522aa",
            provenance: "scene",
          },
        ],
        locked_untouched: [],
      },
    });
    expect(screen.getByTestId("compare-scene-note")).toHaveTextContent("not attached to an element");
    fireEvent.click(screen.getByRole("checkbox", { name: "Only differences" }));
    expect(screen.getByTestId("compare-scene-3")).toHaveAttribute("data-visible", "all");
    expect(screen.getByTestId("compare-scene-2")).toHaveAttribute("data-visible", "all");
  });

  it("shows the candidate basis note and closes through the close control", () => {
    const onClose = vi.fn();
    renderChamber({ candidate: true, basis: "Head vs candidate", onClose });
    expect(screen.getByTestId("compare-candidate-note")).toHaveTextContent("Head-relative comparison");
    fireEvent.click(screen.getByTestId("compare-close"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
