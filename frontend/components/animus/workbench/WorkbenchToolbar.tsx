"use client";

import { useRef, type KeyboardEvent } from "react";
import type { GizmoMode, StageLayer, WorkbenchView } from "@/lib/workbenchState";

const VIEWS: Array<{ id: WorkbenchView; label: string; hint: string }> = [
  { id: "stage", label: "Stage", hint: "Spatial view" },
  { id: "structure", label: "Structure", hint: "Graph and relations" },
  { id: "ledger", label: "Ledger", hint: "Versions and branches" },
  { id: "trace", label: "Trace", hint: "What the system did, in order" },
];

const LAYERS: Array<{ id: StageLayer; label: string }> = [
  { id: "relations", label: "Relations" },
  { id: "labels", label: "Labels" },
  { id: "locks", label: "Locks" },
  { id: "provenance", label: "Sources" },
  { id: "grid", label: "Grid" },
  { id: "changes", label: "Changes" },
];

const SHOTS: Array<{ id: string; label: string; hint: string }> = [
  { id: "wide", label: "Wide", hint: "Establishing view of the whole scene" },
  { id: "eye", label: "Eye", hint: "Low eye-level view" },
  { id: "detail", label: "Detail", hint: "Close view of the selected element" },
  { id: "top", label: "Top", hint: "Overhead plan view" },
];

const GIZMOS: Array<{ id: GizmoMode; label: string; key: string }> = [
  { id: "translate", label: "Move", key: "G" },
  { id: "rotate", label: "Rotate", key: "R" },
  { id: "scale", label: "Scale", key: "S" },
];

export default function WorkbenchToolbar({
  view,
  onView,
  layers,
  onToggleLayer,
  gizmoMode,
  onGizmoMode,
  hasSelection,
  selectionLocked,
  readOnly,
  focusMode,
  onToggleFocus,
  cameraPreset,
  onCameraPreset,
}: {
  view: WorkbenchView;
  onView: (view: WorkbenchView) => void;
  layers: Record<StageLayer, boolean>;
  onToggleLayer: (layer: StageLayer) => void;
  gizmoMode: GizmoMode;
  onGizmoMode: (mode: GizmoMode) => void;
  hasSelection: boolean;
  selectionLocked: boolean;
  readOnly: boolean;
  focusMode: boolean;
  onToggleFocus: () => void;
  cameraPreset: string | null;
  onCameraPreset: (preset: string) => void;
}) {
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([]);

  const moveTab = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    let next = index;
    if (event.key === "ArrowRight") next = (index + 1) % VIEWS.length;
    else if (event.key === "ArrowLeft") next = (index - 1 + VIEWS.length) % VIEWS.length;
    else if (event.key === "Home") next = 0;
    else if (event.key === "End") next = VIEWS.length - 1;
    else return;
    event.preventDefault();
    onView(VIEWS[next].id);
    window.requestAnimationFrame(() => tabRefs.current[next]?.focus());
  };

  return (
    <div className="border-b border-white/[0.07] bg-[#080a0c]/80">
      <div className="flex flex-wrap items-center gap-2 px-3 py-2">
        <div
          role="tablist"
          aria-label="Workbench view"
          aria-orientation="horizontal"
          className="flex items-center gap-1 rounded-lg border border-white/10 bg-white/[0.025] p-0.5"
        >
          {VIEWS.map((item, index) => (
            <button
              key={item.id}
              ref={(node) => {
                tabRefs.current[index] = node;
              }}
              type="button"
              role="tab"
              aria-selected={view === item.id}
              aria-controls={`workbench-view-${item.id}`}
              tabIndex={view === item.id ? 0 : -1}
              data-testid={`workbench-tab-${item.id}`}
              onClick={() => onView(item.id)}
              onKeyDown={(event) => moveTab(event, index)}
              title={item.hint}
              className={`inline-flex min-h-8 items-center rounded-md px-2.5 text-xs font-medium transition-colors ${
                view === item.id
                  ? "bg-signal/12 text-signal"
                  : "text-foreground/50 hover:bg-white/[0.04] hover:text-foreground/85"
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>

        <span className="hidden h-5 w-px bg-white/10 sm:block" aria-hidden="true" />

        {view === "stage" ? (
          <>
            <div className="flex items-center gap-0.5" role="group" aria-label="Transform tool">
              {GIZMOS.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  aria-pressed={gizmoMode === item.id}
                  aria-keyshortcuts={item.key}
                  disabled={!hasSelection || selectionLocked || readOnly}
                  onClick={() => onGizmoMode(item.id)}
                  title={
                    !hasSelection
                      ? "Select an element first"
                      : selectionLocked
                        ? "Unlock the element to transform it"
                        : readOnly
                          ? "Preview is read-only"
                          : `${item.label} (${item.key})`
                  }
                  className={`rounded-md border px-2 py-1 text-[11px] transition-colors disabled:opacity-30 ${
                    gizmoMode === item.id
                      ? "border-signal/35 bg-signal/10 text-signal"
                      : "border-white/10 text-foreground/45 hover:text-foreground/80"
                  }`}
                >
                  {item.label}
                </button>
              ))}
            </div>

            <details className="group relative">
              <summary className="list-none rounded-md border border-white/10 px-2 py-1 text-[11px] text-foreground/45 hover:text-foreground/80 [&::-webkit-details-marker]:hidden">
                Layers
              </summary>
              <div className="absolute left-0 top-8 z-40 w-44 rounded-lg border border-white/12 bg-[#0b0d10] p-2 shadow-2xl">
                {LAYERS.map((layer) => (
                  <label
                    key={layer.id}
                    className="flex cursor-pointer items-center justify-between gap-2 rounded px-1.5 py-1 text-[11px] text-foreground/55 hover:bg-white/[0.04]"
                  >
                    <span>{layer.label}</span>
                    <input
                      type="checkbox"
                      checked={layers[layer.id]}
                      onChange={() => onToggleLayer(layer.id)}
                      className="accent-[#6fe3c4]"
                    />
                  </label>
                ))}
              </div>
            </details>

            <div className="flex items-center gap-0.5" role="group" aria-label="Camera shot">
              <span className="mr-1 hidden font-mono text-[11px] uppercase tracking-[0.14em] text-foreground/25 lg:inline">
                Shot
              </span>
              {SHOTS.map((shot) => (
                <button
                  key={shot.id}
                  type="button"
                  onClick={() => onCameraPreset(shot.id)}
                  aria-pressed={cameraPreset === shot.id}
                  title={shot.hint}
                  className={`rounded-md border px-2 py-1 text-[11px] transition-colors ${
                    cameraPreset === shot.id
                      ? "border-signal/35 bg-signal/10 text-signal"
                      : "border-white/10 text-foreground/45 hover:text-foreground/80"
                  }`}
                >
                  {shot.label}
                </button>
              ))}
            </div>
          </>
        ) : null}

        <button
          type="button"
          onClick={onToggleFocus}
          aria-pressed={focusMode}
          className={`ml-auto rounded-md border px-2 py-1 text-[11px] transition-colors ${
            focusMode
              ? "border-lock/35 bg-lock/10 text-lock"
              : "border-white/10 text-foreground/45 hover:text-foreground/80"
          }`}
          title="Hide the candidate strip and non-essential chrome (F)"
        >
          {focusMode ? "Focus on" : "Focus"}
        </button>
        {readOnly ? (
          <span className="rounded-full border border-lock/35 bg-lock/10 px-2 py-1 font-mono text-[11px] uppercase tracking-[0.16em] text-lock">
            preview · read only
          </span>
        ) : null}
      </div>
    </div>
  );
}
