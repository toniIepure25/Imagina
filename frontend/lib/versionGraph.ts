import type { BranchSummary, VersionSummary } from "@/lib/animusStudioApi";

export interface VersionGraphNode {
  version: VersionSummary;
  x: number;
  y: number;
  lane: number;
}

export interface VersionGraphEdge {
  from: VersionGraphNode;
  to: VersionGraphNode;
  path: string;
}

export interface VersionGraphLayout {
  width: number;
  height: number;
  nodes: VersionGraphNode[];
  edges: VersionGraphEdge[];
  lanes: Array<{ branch: BranchSummary; y: number }>;
}

const PADDING_X = 52;
const PADDING_Y = 34;
const COLUMN_WIDTH = 84;
const LANE_HEIGHT = 58;

export function buildVersionGraph(
  versions: VersionSummary[],
  branches: BranchSummary[],
  activeBranchId?: string,
): VersionGraphLayout {
  const orderedBranches = branches.slice().sort((a, b) => {
    if (a.branch_id === activeBranchId) return -1;
    if (b.branch_id === activeBranchId) return 1;
    return a.created_at.localeCompare(b.created_at);
  });
  const laneByBranch = new Map(orderedBranches.map((branch, index) => [branch.branch_id, index]));
  const ordered = versions.slice().sort((a, b) => a.number - b.number);
  const columns = new Map(ordered.map((version, index) => [version.version_id, index]));
  const nodes = ordered.map<VersionGraphNode>((version) => {
    const lane = laneByBranch.get(version.branch_id) ?? Math.max(0, orderedBranches.length - 1);
    const column = columns.get(version.version_id) ?? 0;
    return {
      version,
      lane,
      x: PADDING_X + column * COLUMN_WIDTH,
      y: PADDING_Y + lane * LANE_HEIGHT,
    };
  });
  const byId = new Map(nodes.map((node) => [node.version.version_id, node]));
  const edges: VersionGraphEdge[] = [];
  for (const node of nodes) {
    const parentId = node.version.parent_version_id;
    if (!parentId) continue;
    const parent = byId.get(parentId);
    if (!parent) continue;
    const middle = (parent.x + node.x) / 2;
    edges.push({
      from: parent,
      to: node,
      path: `M ${parent.x} ${parent.y} C ${middle} ${parent.y}, ${middle} ${node.y}, ${node.x} ${node.y}`,
    });
  }
  const laneCount = Math.max(1, orderedBranches.length);
  return {
    width: Math.max(360, PADDING_X * 2 + Math.max(1, ordered.length - 1) * COLUMN_WIDTH),
    height: PADDING_Y * 2 + (laneCount - 1) * LANE_HEIGHT,
    nodes,
    edges,
    lanes: orderedBranches.map((branch, index) => ({
      branch,
      y: PADDING_Y + index * LANE_HEIGHT,
    })),
  };
}
