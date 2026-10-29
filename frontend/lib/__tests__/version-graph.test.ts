import { describe, expect, it } from "vitest";
import type { BranchSummary, VersionSummary } from "@/lib/animusStudioApi";
import { buildVersionGraph } from "@/lib/versionGraph";

function version(number: number, branch = "b1", parent: string | null = null): VersionSummary {
  return {
    version_id: `v${number}`,
    number,
    branch_id: branch,
    parent_version_id: parent,
    source: "user",
    label: `Version ${number}`,
    intention: null,
    claim_level: "L1_BEHAVIORAL_ASSISTED",
    created_at: `2026-10-2${number}T10:00:00Z`,
    content_hash: `hash-${number}`,
    entity_count: number,
  };
}

function branch(id: string, active = false): BranchSummary {
  return {
    branch_id: id,
    name: id,
    head_version_id: "",
    created_at: "2026-10-20T10:00:00Z",
    parent_branch_id: null,
    fork_version_id: null,
    is_active: active,
  };
}

describe("buildVersionGraph", () => {
  it("places versions in columns and lanes", () => {
    const layout = buildVersionGraph(
      [version(1, "b1"), version(2, "b1", "v1"), version(3, "b2", "v2")],
      [branch("b1", true), branch("b2")],
      "b1",
    );
    expect(layout.nodes).toHaveLength(3);
    expect(layout.nodes[0].x).toBeLessThan(layout.nodes[1].x);
    expect(layout.nodes[2].lane).toBe(1);
    expect(layout.edges).toHaveLength(2);
    expect(layout.edges[1].path).toContain("C");
  });

  it("handles a single version without inventing edges", () => {
    const layout = buildVersionGraph([version(1)], [branch("b1", true)]);
    expect(layout.nodes).toHaveLength(1);
    expect(layout.edges).toHaveLength(0);
    expect(layout.width).toBeGreaterThanOrEqual(360);
  });

  it("keeps version order stable even when input is unordered", () => {
    const layout = buildVersionGraph([version(3, "b1", "v2"), version(1), version(2, "b1", "v1")], [branch("b1")]);
    expect(layout.nodes.map((node) => node.version.number)).toEqual([1, 2, 3]);
  });
});
