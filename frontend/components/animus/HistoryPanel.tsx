"use client";

import { useState } from "react";
import Button from "@/components/common/Button";
import type { BranchSummary, VersionSummary } from "@/lib/animusStudioApi";
import { formatTime } from "./sceneUtils";

const SOURCE_LABELS: Record<string, string> = {
  seed: "seed",
  intention: "intention",
  command: "command",
  candidate: "candidate",
  undo: "undo",
  redo: "redo",
  branch: "branch",
};

export default function HistoryPanel({
  versions,
  branches,
  activeBranchId,
  activeVersionId,
  hasUndo,
  hasRedo,
  busy,
  onUndo,
  onRedo,
  onBranch,
  onSwitchBranch,
}: {
  versions: VersionSummary[];
  branches: BranchSummary[];
  activeBranchId: string;
  activeVersionId: string;
  hasUndo: boolean;
  hasRedo: boolean;
  busy: boolean;
  onUndo: () => Promise<unknown>;
  onRedo: () => Promise<unknown>;
  onBranch: (name?: string, fromVersionId?: string) => Promise<unknown>;
  onSwitchBranch: (branchId: string) => Promise<unknown>;
}) {
  const [branchName, setBranchName] = useState("");

  const createBranch = async (fromVersionId?: string) => {
    const name = branchName.trim() || undefined;
    await onBranch(name, fromVersionId);
    setBranchName("");
  };

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-2">
        <Button size="sm" variant="secondary" disabled={busy || !hasUndo} onClick={() => void onUndo()}>
          Undo
        </Button>
        <Button size="sm" variant="secondary" disabled={busy || !hasRedo} onClick={() => void onRedo()}>
          Redo
        </Button>
      </div>

      <div>
        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-[10px] uppercase tracking-[0.18em] text-foreground/40">Versions</h3>
          <span className="font-mono text-[9px] text-foreground/25">{versions.length} total</span>
        </div>
        <ol className="relative space-y-1.5 border-l border-white/10 pl-3">
          {versions
            .slice()
            .reverse()
            .map((version) => {
              const active = version.version_id === activeVersionId;
              return (
                <li key={version.version_id} className="relative">
                  <span
                    className={`absolute -left-[17px] top-2 h-2 w-2 rounded-full border ${
                      active ? "border-accent-glow bg-accent-glow" : "border-white/25 bg-background"
                    }`}
                  />
                  <div
                    className={`rounded-md border px-2.5 py-2 ${
                      active ? "border-accent-glow/30 bg-accent-glow/[0.05]" : "border-transparent hover:bg-white/[0.025]"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-[11px] font-medium text-foreground/75">
                        v{version.number} · {SOURCE_LABELS[version.source] || version.source}
                      </span>
                      <span className="font-mono text-[9px] text-foreground/30">
                        {version.content_hash.slice(0, 7)}
                      </span>
                    </div>
                    <p className="mt-0.5 line-clamp-2 text-[10px] leading-relaxed text-foreground/35">
                      {version.label || version.intention || "Scene version"}
                    </p>
                    <div className="mt-1 flex items-center justify-between">
                      <span className="text-[9px] text-foreground/25">{formatTime(version.created_at)}</span>
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => void createBranch(version.version_id)}
                        className="text-[9px] text-accent-glow/50 hover:text-accent-glow disabled:opacity-40"
                      >
                        branch from here
                      </button>
                    </div>
                  </div>
                </li>
              );
            })}
        </ol>
      </div>

      <div className="space-y-2 border-t border-white/10 pt-3">
        <h3 className="text-[10px] uppercase tracking-[0.18em] text-foreground/40">Branches</h3>
        <div className="space-y-1.5">
          {branches.map((branch) => {
            const active = branch.branch_id === activeBranchId;
            return (
              <div
                key={branch.branch_id}
                className={`flex items-center justify-between rounded-md border px-2.5 py-1.5 ${
                  active ? "border-accent-glow/30 bg-accent-glow/[0.05]" : "border-white/8 bg-white/[0.015]"
                }`}
              >
                <div className="min-w-0">
                  <div className="truncate text-[11px] text-foreground/70">{branch.name}</div>
                  <div className="text-[9px] text-foreground/25">{formatTime(branch.created_at)}</div>
                </div>
                {active ? (
                  <span className="text-[9px] uppercase tracking-wide text-accent-glow/60">active</span>
                ) : (
                  <button
                    type="button"
                    data-testid="branch-switch"
                    disabled={busy}
                    onClick={() => void onSwitchBranch(branch.branch_id)}
                    aria-label={`Switch to branch ${branch.name}`}
                    className="text-[10px] text-foreground/45 hover:text-foreground disabled:opacity-40"
                  >
                    switch
                  </button>
                )}
              </div>
            );
          })}
        </div>
        <div className="flex gap-1.5 pt-1">
          <input
            data-testid="branch-name"
            value={branchName}
            onChange={(event) => setBranchName(event.target.value)}
            maxLength={40}
            placeholder="New branch name"
            className="min-w-0 flex-1 rounded-md border border-white/10 bg-white/[0.03] px-2 py-1.5 text-[10px] outline-none placeholder:text-foreground/25 focus:border-accent-glow/40"
          />
          <Button size="sm" variant="secondary" disabled={busy} onClick={() => void createBranch()}>
            Create
          </Button>
        </div>
      </div>
    </div>
  );
}
