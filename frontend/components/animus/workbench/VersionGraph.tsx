"use client";

import { useMemo } from "react";
import type { BranchSummary, VersionSummary } from "@/lib/animusStudioApi";
import { buildVersionGraph } from "@/lib/versionGraph";
import { formatRelative } from "../sceneUtils";

export default function VersionGraph({
  versions,
  branches,
  activeVersionId,
  previewVersionId,
  onPreview,
  onBranch,
  busy,
}: {
  versions: VersionSummary[];
  branches: BranchSummary[];
  activeVersionId: string;
  previewVersionId: string | null;
  onPreview: (versionId: string) => void;
  onBranch: (versionId: string) => void;
  busy: boolean;
}) {
  const layout = useMemo(
    () => buildVersionGraph(versions, branches, branches.find((branch) => branch.is_active)?.branch_id),
    [branches, versions],
  );
  const branchName = useMemo(() => new Map(branches.map((branch) => [branch.branch_id, branch.name])), [branches]);

  return (
    <div className="instrument-panel overflow-hidden rounded-lg">
      <div className="flex items-center justify-between gap-3 border-b border-white/8 px-3 py-2">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-signal/60">Version ledger</p>
          <p className="mt-0.5 text-[11px] text-foreground/35">
            Preview any version without changing the head. Branch only when you choose.
          </p>
        </div>
        <span className="shrink-0 font-mono text-[11px] text-foreground/30">
          {versions.length} version{versions.length === 1 ? "" : "s"}
        </span>
      </div>
      <div className="overflow-x-auto p-2">
        <svg
          viewBox={`0 0 ${layout.width} ${Math.max(160, layout.height)}`}
          className="min-w-[560px]"
          style={{ width: layout.width, height: Math.max(160, layout.height) }}
          role="group"
          aria-label="Version and branch graph"
        >
          {layout.lanes.map((lane) => (
            <g key={lane.branch.branch_id}>
              <line x1="12" y1={lane.y} x2={layout.width - 12} y2={lane.y} stroke="rgba(236,231,218,0.055)" strokeWidth="18" />
              <text x="14" y={lane.y - 10} fill="rgba(236,231,218,0.38)" fontSize="11" fontFamily="ui-monospace, monospace">
                {lane.branch.name.slice(0, 18)}
              </text>
            </g>
          ))}
          {layout.edges.map((edge) => (
            <path
              key={`${edge.from.version.version_id}-${edge.to.version.version_id}`}
              d={edge.path}
              fill="none"
              stroke="rgba(236,231,218,0.22)"
              strokeWidth="1.2"
            />
          ))}
          {layout.nodes.map((node) => {
            const active = node.version.version_id === activeVersionId;
            const preview = node.version.version_id === previewVersionId;
            return (
              <g
                key={node.version.version_id}
                role="button"
                tabIndex={0}
                aria-label={`Version ${node.version.number} on ${branchName.get(node.version.branch_id) ?? "branch"}, ${formatRelative(node.version.created_at)}${active ? ", current head" : ""}`}
                onClick={() => onPreview(node.version.version_id)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    onPreview(node.version.version_id);
                  }
                }}
                style={{ cursor: "pointer" }}
                data-testid={`ledger-node-${node.version.version_id}`}
              >
                <title>{`v${node.version.number} · ${branchName.get(node.version.branch_id) ?? "branch"}${active ? " · head" : ""}`}</title>
                <circle cx={node.x} cy={node.y} r={active || preview ? 13 : 10} fill="transparent" />
                <circle
                  cx={node.x}
                  cy={node.y}
                  r={active ? 7.5 : 6}
                  fill={active ? "#6fe3c4" : preview ? "#e8b45a" : "#14181c"}
                  stroke={active ? "#6fe3c4" : preview ? "#e8b45a" : "rgba(236,231,218,0.45)"}
                  strokeWidth={active || preview ? 2 : 1.2}
                />
                <text x={node.x} y={node.y + 22} textAnchor="middle" fontSize="11" fontFamily="ui-monospace, monospace" fill={active ? "#6fe3c4" : "rgba(236,231,218,0.5)"}>
                  v{node.version.number}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
      <div className="flex flex-wrap gap-2 border-t border-white/8 px-3 py-2">
        {versions.slice().reverse().slice(0, 6).map((version) => (
          <button
            key={version.version_id}
            type="button"
            onClick={() => onPreview(version.version_id)}
            className={`rounded border px-2 py-1 font-mono text-[11px] transition-colors ${
              version.version_id === previewVersionId
                ? "border-lock/40 bg-lock/10 text-lock"
                : version.version_id === activeVersionId
                  ? "border-signal/35 bg-signal/10 text-signal"
                  : "border-white/10 text-foreground/45 hover:text-foreground/75"
            }`}
          >
            v{version.number} · {version.version_id === activeVersionId ? "head" : "preview"}
          </button>
        ))}
        <button
          type="button"
          disabled={!previewVersionId || previewVersionId === activeVersionId || busy}
          onClick={() => previewVersionId && onBranch(previewVersionId)}
          className="ml-auto rounded border border-white/12 px-2 py-1 text-[11px] text-foreground/50 hover:text-foreground disabled:opacity-30"
        >
          Branch from preview
        </button>
      </div>
    </div>
  );
}
