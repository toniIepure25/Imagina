"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import AnimusScene, { type AnimusCameraView } from "@/components/animus/AnimusScene";
import type { SceneGraph } from "@/lib/animusStudioApi";
import type { SceneComparison } from "@/lib/sceneCompare";
import { comparisonSets } from "@/lib/sceneCompare";
import { useFocusTrap } from "@/lib/useFocusTrap";
import { DEFAULT_LAYERS, type StageLayer } from "@/lib/workbenchState";

const HEAD_LAYERS: Record<StageLayer, boolean> = {
  ...DEFAULT_LAYERS,
  relations: false,
  labels: false,
  locks: false,
  provenance: false,
  changes: false,
  grid: true,
};

const PREVIEW_LAYERS: Record<StageLayer, boolean> = {
  ...HEAD_LAYERS,
  changes: true,
};

const noop = () => {};

export default function CompareChamber({
  head,
  preview,
  diff,
  headLabel,
  previewLabel,
  basis,
  candidate = false,
  onClose,
}: {
  head: SceneGraph;
  preview: SceneGraph;
  diff: SceneComparison;
  headLabel: string;
  previewLabel: string;
  basis: string;
  candidate?: boolean;
  onClose: () => void;
}) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const [onlyDifferences, setOnlyDifferences] = useState(false);
  useFocusTrap(true, dialogRef);

  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, []);

  const sets = useMemo(() => comparisonSets(diff), [diff]);
  const entityDifferences = sets.added.size + sets.changed.size + sets.removed.size > 0;
  const sceneLevelChanges = diff.changed.some((item) => !item.entity_id);
  const headVisibleIds = useMemo(
    () => (onlyDifferences && entityDifferences ? new Set([...sets.changed, ...sets.removed]) : null),
    [entityDifferences, onlyDifferences, sets],
  );
  const previewVisibleIds = useMemo(
    () => (onlyDifferences && entityDifferences ? new Set([...sets.changed, ...sets.added]) : null),
    [entityDifferences, onlyDifferences, sets],
  );
  const cameraView = useMemo<AnimusCameraView>(
    () => ({
      position: head.camera.position,
      target: head.camera.target,
      fov: head.camera.fov,
    }),
    [head.camera.fov, head.camera.position, head.camera.target],
  );
  const total = diff.added.length + diff.changed.length + diff.removed.length;
  const hasDifferences = total > 0;

  return (
    <div
      className="fixed inset-0 z-[140] flex items-center justify-center bg-[#03040a]/88 p-2 backdrop-blur-md sm:p-5"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="compare-title"
        aria-describedby="compare-summary"
        tabIndex={-1}
        data-testid="compare-chamber"
        className="flex h-full max-h-full w-full max-w-[1500px] flex-col overflow-hidden rounded-xl border border-white/12 bg-[#07090d] shadow-[0_40px_120px_rgba(0,0,0,0.7)]"
      >
        <header className="flex flex-wrap items-start justify-between gap-3 border-b border-white/10 px-4 py-3">
          <div className="min-w-0">
            <p className="font-mono text-[11px] uppercase tracking-[0.24em] text-signal/70">Comparison chamber</p>
            <h2 id="compare-title" className="mt-1 font-display text-lg text-foreground/90">
              Head and preview, one camera
            </h2>
            <p data-testid="compare-basis" className="mt-1 font-mono text-[11px] text-foreground/40">
              {basis} · <span className="text-signal">+{diff.added.length} added</span> ·{" "}
              <span className="text-lock">~{diff.changed.length} changed</span> ·{" "}
              <span className="text-red-300/80">−{diff.removed.length} removed</span>
            </p>
            {candidate ? (
              <p data-testid="compare-candidate-note" className="mt-1 text-[11px] leading-relaxed text-foreground/35">
                Head-relative comparison. The preview panel reports changes from the candidate&apos;s source version.
              </p>
            ) : null}
            {sceneLevelChanges ? (
              <p data-testid="compare-scene-note" className="mt-1 text-[11px] leading-relaxed text-foreground/35">
                Scene-level changes are not attached to an element.{" "}
                {entityDifferences
                  ? "Only differences filters elements but cannot hide or ring that field."
                  : "Only differences keeps all elements visible."}
              </p>
            ) : null}
          </div>
          <button
            type="button"
            data-testid="compare-close"
            aria-label="Close comparison chamber"
            onClick={onClose}
            className="rounded-md border border-white/12 px-2.5 py-1.5 text-[11px] text-foreground/55 hover:border-white/25 hover:text-foreground"
          >
            Close
          </button>
        </header>

        <p id="compare-summary" className="sr-only" aria-live="polite">
          Comparison chamber. {headLabel} versus {previewLabel}. {basis}. {diff.added.length} added,{" "}
          {diff.changed.length} changed, and {diff.removed.length} removed change rows.{" "}
          {onlyDifferences
            ? entityDifferences
              ? "Only differences are shown."
              : "Only scene-level differences exist; all elements remain visible."
            : "All elements are shown."}
        </p>

        {!hasDifferences ? (
          <div role="status" className="border-b border-white/8 px-4 py-2 text-[11px] text-foreground/45">
            No differences between head and preview.
          </div>
        ) : null}

        <div className="grid min-h-0 flex-1 grid-rows-2 md:grid-cols-2 md:grid-rows-1">
          <section
            aria-label={`Head scene, ${headLabel}`}
            className="flex min-h-0 flex-col border-b border-white/10 md:border-b-0 md:border-r"
          >
            <div className="flex items-center justify-between gap-2 border-b border-white/8 px-3 py-1.5">
              <span className="font-mono text-[11px] uppercase tracking-[0.2em] text-foreground/45">Head</span>
              <span className="truncate font-mono text-[11px] text-foreground/30">{headLabel}</span>
            </div>
            <div className="relative min-h-0 flex-1">
              <AnimusScene
                scene={head}
                selectedId={null}
                onSelect={noop}
                className="h-full w-full"
                showOverlay={false}
                interactive={false}
                layers={HEAD_LAYERS}
                readOnly
                cameraView={cameraView}
                visibleIds={headVisibleIds}
                animate={false}
                frameloop="demand"
                dpr={[1, 1.35]}
              />
            </div>
          </section>

          <section aria-label={`Preview scene, ${previewLabel}`} className="flex min-h-0 flex-col">
            <div className="flex items-center justify-between gap-2 border-b border-white/8 px-3 py-1.5">
              <span className="font-mono text-[11px] uppercase tracking-[0.2em] text-lock/75">Preview</span>
              <span className="truncate font-mono text-[11px] text-foreground/30">{previewLabel}</span>
            </div>
            <div className="relative min-h-0 flex-1">
              <AnimusScene
                scene={preview}
                selectedId={null}
                onSelect={noop}
                className="h-full w-full"
                showOverlay={false}
                interactive={false}
                layers={PREVIEW_LAYERS}
                readOnly
                cameraView={cameraView}
                diff={diff}
                traceScene={head}
                visibleIds={previewVisibleIds}
                animate={false}
                frameloop="demand"
                dpr={[1, 1.35]}
              />
            </div>
          </section>
        </div>

        <footer className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 border-t border-white/10 px-4 py-2.5">
          <label className="inline-flex cursor-pointer items-center gap-2 text-[11px] text-foreground/55">
            <input
              type="checkbox"
              data-testid="compare-only-differences"
              checked={onlyDifferences}
              disabled={!hasDifferences}
              onChange={(event) => setOnlyDifferences(event.target.checked)}
              className="h-3.5 w-3.5 accent-[#6fe3c4]"
            />
            Only differences
          </label>
          <div data-testid="compare-legend" className="flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-[11px] text-foreground/35">
            <span className="inline-flex items-center gap-1">
              <span className="h-1.5 w-1.5 rounded-full bg-signal" /> solid · added
            </span>
            <span className="inline-flex items-center gap-1">
              <span className="h-1.5 w-1.5 rounded-full bg-lock" /> dashed · changed
            </span>
            <span className="inline-flex items-center gap-1">
              <span className="h-1.5 w-1.5 rounded-full bg-red-300/80" /> trace · removed or moved from
            </span>
            <span className="inline-flex items-center gap-1">
              <span className="h-1.5 w-1.5 rounded-full bg-foreground/30" /> unchanged
            </span>
          </div>
          <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-foreground/25">
            shared camera · L1 behavioral
          </p>
        </footer>
      </div>
    </div>
  );
}
