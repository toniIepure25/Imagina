"use client";

import type { StudioSnapshot } from "@/lib/animusStudioApi";
import { formatRelative } from "../sceneUtils";
import VersionGraph from "./VersionGraph";

export default function LedgerView({
  snapshot,
  previewVersionId,
  onPreview,
  onBranch,
  onTrace,
  busy,
}: {
  snapshot: StudioSnapshot;
  previewVersionId: string | null;
  onPreview: (versionId: string) => void;
  onBranch: (versionId: string) => void;
  onTrace: () => void;
  busy: boolean;
}) {
  const activeBranch = snapshot.branches.find((branch) => branch.is_active);
  return (
    <div className="grid gap-3 p-3 xl:grid-cols-[minmax(0,1fr)_300px]">
      <div className="min-w-0 space-y-3">
        <VersionGraph
          versions={snapshot.history}
          branches={snapshot.branches}
          activeVersionId={snapshot.active_version_id}
          previewVersionId={previewVersionId}
          onPreview={onPreview}
          onBranch={onBranch}
          busy={busy}
        />
        <div className="instrument-panel rounded-lg p-3">
          <div className="flex items-center justify-between gap-3">
            <h2 className="mono-label text-foreground/40">Recent versions</h2>
            <div className="flex items-center gap-2">
              <span className="font-mono text-[11px] text-foreground/35">head v{snapshot.version.number}</span>
              <button
                type="button"
                onClick={onTrace}
                className="inline-flex min-h-8 items-center rounded-md border border-signal/25 px-2 text-xs text-signal/85 hover:bg-signal/10"
              >
                Trace
              </button>
            </div>
          </div>
          <ol className="mt-2 divide-y divide-white/[0.07]">
            {snapshot.history
              .slice()
              .reverse()
              .slice(0, 8)
              .map((version) => (
                <li key={version.version_id} className="flex items-start gap-2 py-2">
                  <button
                    type="button"
                    onClick={() => onPreview(version.version_id)}
                    className={`min-w-0 flex-1 text-left transition-colors ${
                      version.version_id === previewVersionId ? "text-lock" : "text-foreground/70 hover:text-foreground"
                    }`}
                  >
                    <span className="block text-sm">
                      v{version.number} · {version.label}
                    </span>
                    <span className="mt-0.5 block font-mono text-[11px] text-foreground/40">
                      {version.entity_count} elements · {formatRelative(version.created_at)} · {version.source}
                    </span>
                  </button>
                  {version.version_id === snapshot.active_version_id ? (
                    <span className="shrink-0 rounded-full border border-signal/30 px-2 py-0.5 font-mono text-[11px] uppercase text-signal">
                      head
                    </span>
                  ) : (
                    <button
                      type="button"
                      onClick={() => onBranch(version.version_id)}
                      disabled={busy}
                      className="inline-flex min-h-7 shrink-0 items-center rounded border border-white/10 px-2 text-[11px] text-foreground/45 hover:text-foreground disabled:opacity-30"
                    >
                      branch
                    </button>
                  )}
                </li>
              ))}
          </ol>
        </div>
      </div>
      <aside className="space-y-3">
        <section className="instrument-panel rounded-lg p-3">
          <h2 className="mono-label text-foreground/40">Branches</h2>
          <ul className="mt-2 space-y-1.5">
            {snapshot.branches.map((branch) => (
              <li
                key={branch.branch_id}
                className="flex items-center justify-between gap-2 rounded border border-white/8 px-2 py-1.5"
              >
                <span className={`min-w-0 truncate text-xs ${branch.is_active ? "text-signal" : "text-foreground/65"}`}>
                  {branch.name}
                </span>
                <span className="shrink-0 font-mono text-[11px] uppercase text-foreground/35">
                  {branch.is_active ? "active" : branch.fork_version_id ? "fork" : "branch"}
                </span>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-xs leading-5 text-foreground/45">
            A version is immutable. Previewing never writes. Branching preserves the current head and creates a new
            place to explore.
          </p>
        </section>
        <section className="instrument-panel rounded-lg p-3">
          <h2 className="mono-label text-foreground/40">Intentions</h2>
          <ol className="mt-2 space-y-2">
            {snapshot.history
              .slice()
              .reverse()
              .filter((version) => version.intention)
              .slice(0, 4)
              .map((version) => (
                <li key={version.version_id} className="text-xs leading-5 text-foreground/55">
                  <span className="mr-1 font-mono text-[11px] text-foreground/35">v{version.number}</span>
                  {version.intention}
                </li>
              ))}
            {snapshot.history.every((version) => !version.intention) ? (
              <li className="text-xs text-foreground/40">No recorded intention yet.</li>
            ) : null}
          </ol>
        </section>
        {activeBranch ? (
          <p className="px-1 font-mono text-[11px] uppercase tracking-[0.14em] text-foreground/30">
            active branch · {activeBranch.name}
          </p>
        ) : null}
      </aside>
    </div>
  );
}
