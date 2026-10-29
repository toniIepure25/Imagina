import { describe, expect, it } from "vitest";
import { DEFAULT_LAYERS, INITIAL_WORKBENCH_STATE, workbenchReducer } from "@/lib/workbenchState";
import type { StudioCandidate } from "@/lib/animusStudioApi";

const candidate = {
  candidate_id: "c1",
  source_version_id: "v1",
} as StudioCandidate;

describe("workbenchReducer", () => {
  it("changes views without mutating layers", () => {
    const next = workbenchReducer(INITIAL_WORKBENCH_STATE, { type: "view", view: "structure" });
    expect(next.view).toBe("structure");
    expect(next.layers).toBe(DEFAULT_LAYERS);
  });

  it("toggles one layer and preserves the others", () => {
    const next = workbenchReducer(INITIAL_WORKBENCH_STATE, { type: "layer", layer: "grid" });
    expect(next.layers.grid).toBe(true);
    expect(next.layers.relations).toBe(true);
  });

  it("clears focus when a preview opens", () => {
    const focused = workbenchReducer(INITIAL_WORKBENCH_STATE, { type: "focus", enabled: true });
    const previewing = workbenchReducer(focused, {
      type: "preview",
      preview: { kind: "candidate", candidate },
    });
    expect(previewing.focusMode).toBe(false);
    expect(previewing.preview?.kind).toBe("candidate");
  });

  it("prunes a selection that is no longer present", () => {
    const selected = workbenchReducer(INITIAL_WORKBENCH_STATE, { type: "select", entityId: "gone" });
    const pruned = workbenchReducer(selected, { type: "prune_selection", entityIds: ["kept"] });
    expect(pruned.selectedId).toBeNull();
  });

  it("keeps a selection that still exists", () => {
    const selected = workbenchReducer(INITIAL_WORKBENCH_STATE, { type: "select", entityId: "kept" });
    const pruned = workbenchReducer(selected, { type: "prune_selection", entityIds: ["kept"] });
    expect(pruned.selectedId).toBe("kept");
  });
});
