"use client";

import type { SceneDiff } from "@/lib/animusStudioApi";
import type { SceneComparison } from "@/lib/sceneCompare";
import type { WorkbenchPreview } from "@/lib/workbenchState";

function previewTitle(preview: WorkbenchPreview): string {
  if (!preview) return "";
  if (preview.kind === "candidate") {
    return `Candidate ${String.fromCharCode(65 + preview.candidate.variant_index)}`;
  }
  return `Version ${preview.version.number}`;
}

function previewDetail(preview: WorkbenchPreview): string {
  if (!preview) return "";
  if (preview.kind === "candidate") {
    return "Generated from the current head. Keep it to create a new version.";
  }
  return `From ${preview.version.branch_id} · ${preview.version.label}`;
}

function BlinkButton({
  active,
  disabled,
  onClick,
  label,
}: {
  active: boolean;
  disabled: boolean;
  onClick: () => void;
  label: string;
}) {
  return (
    <button
      type="button"
      data-testid="blink-button"
      onClick={onClick}
      disabled={disabled}
      aria-pressed={active}
      aria-label={active ? "Stop blink comparison" : "Blink head and preview in the same camera"}
      title={
        active
          ? "Stop the manual blink comparison"
          : "Manually alternate head and preview in the same camera. Never automatic."
      }
      className={`inline-flex min-h-7 items-center gap-1 rounded border px-2 text-[11px] transition-colors disabled:opacity-35 ${
        active
          ? "border-lock/50 bg-lock/15 text-lock"
          : "border-white/12 bg-white/[0.02] text-foreground/60 hover:border-lock/35 hover:text-lock/90"
      }`}
    >
      <span aria-hidden="true" className="font-mono text-[11px]">
        ◐
      </span>
      {active ? "Stop blink" : label}
    </button>
  );
}

export default function PreviewBanner({
  preview,
  stale,
  busy,
  blinkOn,
  onBlink,
  onKeep,
  onDiscard,
  onBranch,
  onCompare,
}: {
  preview: WorkbenchPreview;
  stale: boolean;
  busy: boolean;
  blinkOn: boolean;
  onBlink: () => void;
  onKeep: () => void;
  onDiscard: () => void;
  onBranch: () => void;
  onCompare: () => void;
}) {
  if (!preview) return null;
  return (
    <div
      role="status"
      data-testid="preview-banner"
      className="flex flex-wrap items-center gap-2 border-b border-lock/25 bg-lock/[0.07] px-3 py-2"
    >
      <span className="grid h-7 w-7 place-items-center rounded-full border border-lock/40 font-mono text-[11px] text-lock">
        P
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-xs font-medium text-lock">
          Previewing {previewTitle(preview)} <span className="font-normal text-lock/65">— not committed</span>
        </p>
        <p className="truncate text-[11px] text-foreground/45">
          {stale ? "This preview is from an older head. Return or regenerate before keeping it." : previewDetail(preview)}
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-1.5">
        <BlinkButton
          active={blinkOn}
          disabled={busy || stale}
          onClick={onBlink}
          label="Blink"
        />
        <button
          type="button"
          data-testid="compare-banner-button"
          onClick={onCompare}
          disabled={busy || stale}
          aria-label="Compare head and preview"
          title={stale ? "The head changed after this preview opened" : "Compare head and preview side by side"}
          className="inline-flex min-h-7 items-center rounded border border-signal/25 bg-signal/[0.06] px-2 text-[11px] text-signal/85 hover:border-signal/45 disabled:opacity-35"
        >
          Compare
        </button>
        {preview.kind === "version" ? (
          <button
            type="button"
            onClick={onBranch}
            disabled={busy}
            className="inline-flex min-h-7 items-center rounded border border-white/12 px-2 text-[11px] text-foreground/60 hover:text-foreground disabled:opacity-35"
          >
            Branch from here
          </button>
        ) : (
          <button
            type="button"
            onClick={onKeep}
            disabled={busy || stale}
            className="inline-flex min-h-7 items-center rounded border border-signal/35 bg-signal/10 px-2 text-[11px] text-signal disabled:opacity-35"
          >
            Keep this
          </button>
        )}
        <button
          type="button"
          onClick={onDiscard}
          disabled={busy}
          className="inline-flex min-h-7 items-center rounded border border-white/12 px-2 text-[11px] text-foreground/50 hover:text-foreground disabled:opacity-35"
        >
          Return to head
        </button>
      </div>
    </div>
  );
}

export function PreviewPanel({
  preview,
  diff,
  diffBasis,
  stale,
  busy,
  blinkOn = false,
  focusableIds,
  onFocusEntity,
  onBlink = () => {},
  onKeep,
  onDiscard,
  onBranch,
  onCompare,
}: {
  preview: WorkbenchPreview;
  diff: SceneDiff | SceneComparison | null;
  diffBasis: string;
  stale: boolean;
  busy: boolean;
  blinkOn?: boolean;
  focusableIds: Set<string>;
  onFocusEntity: (entityId: string) => void;
  onBlink?: () => void;
  onKeep: () => void;
  onDiscard: () => void;
  onBranch: () => void;
  onCompare: () => void;
}) {
  if (!preview) return null;
  const added = diff?.added.length ?? 0;
  const removed = diff?.removed.length ?? 0;
  const changed = diff?.changed.length ?? 0;
  const explanation = diff && "explanation" in diff ? diff.explanation : null;
  return (
    <div data-testid="preview-panel" className="flex h-full flex-col p-3">
      <p className="mono-label text-lock/75">Read-only preview</p>
      <h2 className="mt-1 font-display text-xl text-foreground/90">{previewTitle(preview)}</h2>
      <p className="mt-1 text-xs leading-5 text-foreground/45">{previewDetail(preview)}</p>
      <p data-testid="diff-basis" className="mt-1 font-mono text-[11px] uppercase tracking-[0.12em] text-foreground/35">
        Diff basis · {diffBasis}
      </p>
      {stale ? (
        <p role="alert" className="mt-3 rounded border border-lock/30 bg-lock/10 px-2 py-1.5 text-xs leading-5 text-lock/85">
          The head changed after this preview was opened. It cannot be committed. Return and explore again.
        </p>
      ) : null}
      <dl className="mt-4 grid grid-cols-3 gap-2 text-center">
        <div className="rounded border border-white/8 py-2">
          <dt className="font-mono text-[11px] uppercase text-foreground/35">Added</dt>
          <dd className="mt-0.5 font-mono text-base text-signal">{added}</dd>
        </div>
        <div className="rounded border border-white/8 py-2">
          <dt className="font-mono text-[11px] uppercase text-foreground/35">Changed</dt>
          <dd className="mt-0.5 font-mono text-base text-lock">{changed}</dd>
        </div>
        <div className="rounded border border-white/8 py-2">
          <dt className="font-mono text-[11px] uppercase text-foreground/35">Removed</dt>
          <dd className="mt-0.5 font-mono text-base text-red-300/90">{removed}</dd>
        </div>
      </dl>
      <div className="mt-3 grid gap-1.5">
        <button
          type="button"
          data-testid="compare-preview-button"
          onClick={onCompare}
          disabled={busy || stale}
          title={stale ? "The head changed after this preview opened" : "Compare head and preview side by side"}
          className="w-full rounded border border-signal/30 bg-signal/[0.07] px-2 py-2 text-xs text-signal/85 hover:border-signal/50 disabled:opacity-35"
        >
          Compare with head
        </button>
        <BlinkButton active={blinkOn} disabled={busy || stale} onClick={onBlink} label="Blink head / preview" />
      </div>
      {explanation ? (
        <div className="mt-3 rounded border border-white/8 bg-white/[0.02] p-2.5">
          <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-foreground/35">What changed</p>
          <p className="mt-1 text-xs leading-5 text-foreground/60">{explanation}</p>
        </div>
      ) : null}
      {diff?.changed.length ? (
        <ul className="mt-3 space-y-1.5 overflow-y-auto">
          {diff.changed.slice(0, 8).map((item, index) => {
            const canFocus = Boolean(item.entity_id && focusableIds.has(item.entity_id));
            return (
              <li key={`${item.path}-${index}`} className="rounded border border-white/8 px-2 py-1.5 text-xs">
                <button
                  type="button"
                  data-testid={index === 0 ? "preview-change-row" : undefined}
                  disabled={!canFocus}
                  onClick={() => {
                    if (item.entity_id) onFocusEntity(item.entity_id);
                  }}
                  aria-label={canFocus ? `Focus ${item.label} in the scene` : `${item.label} is not in this preview`}
                  className="w-full text-left disabled:cursor-default"
                >
                  <p className="text-foreground/65">
                    {item.label} · <span className="font-mono text-[11px] text-foreground/40">{item.path}</span>
                  </p>
                  <p className="mt-0.5 flex items-center justify-between gap-2 font-mono text-[11px] text-foreground/40">
                    <span>
                      {String(item.before)} → <span className="text-lock/80">{String(item.after)}</span>
                    </span>
                    <span className="shrink-0 text-[11px] uppercase tracking-[0.1em] text-lock/65">
                      {canFocus ? "Focus" : "Not in scene"}
                    </span>
                  </p>
                </button>
              </li>
            );
          })}
        </ul>
      ) : null}
      {diff?.added.length ? (
        <div className="mt-3">
          <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-foreground/35">Added</p>
          <div className="mt-1 flex flex-wrap gap-1">
            {diff.added.slice(0, 8).map((item) => (
              <button
                key={item.entity_id}
                type="button"
                onClick={() => onFocusEntity(item.entity_id)}
                aria-label={`Focus added ${item.label} in the scene`}
                className="min-h-7 rounded border border-signal/25 bg-signal/[0.06] px-1.5 text-xs text-signal/80 hover:border-signal/50"
              >
                {item.label}
              </button>
            ))}
          </div>
          {diff.added.length > 8 ? (
            <p className="mt-1 font-mono text-[11px] text-foreground/35">+{diff.added.length - 8} more</p>
          ) : null}
        </div>
      ) : null}
      {diff?.removed.length ? (
        <div className="mt-3">
          <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-foreground/35">Removed</p>
          <p className="mt-1 text-xs leading-5 text-red-300/70">
            {diff.removed.slice(0, 8).map((item) => item.label).join(" · ")}
            {diff.removed.length > 8 ? ` · +${diff.removed.length - 8} more` : ""}
          </p>
          <p className="mt-1 font-mono text-[11px] text-foreground/30">
            Previous positions are drawn as trace when available.
          </p>
        </div>
      ) : null}
      {diff?.locked_untouched.length ? (
        <p className="mt-3 text-[11px] leading-5 text-foreground/35">
          Locked and untouched: {diff.locked_untouched.join(", ")}
        </p>
      ) : null}
      <div className="mt-auto space-y-1.5 pt-4">
        {preview.kind === "candidate" ? (
          <button
            type="button"
            onClick={onKeep}
            disabled={busy || stale}
            className="w-full rounded border border-signal/35 bg-signal/10 px-2 py-2 text-xs text-signal disabled:opacity-35"
          >
            Keep this candidate
          </button>
        ) : (
          <button
            type="button"
            onClick={onBranch}
            disabled={busy}
            className="w-full rounded border border-signal/35 bg-signal/10 px-2 py-2 text-xs text-signal disabled:opacity-35"
          >
            Branch from this version
          </button>
        )}
        <button
          type="button"
          onClick={onDiscard}
          disabled={busy}
          className="w-full rounded border border-white/12 px-2 py-2 text-xs text-foreground/50 hover:text-foreground disabled:opacity-35"
        >
          Return to head
        </button>
      </div>
    </div>
  );
}
