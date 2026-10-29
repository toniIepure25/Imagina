"use client";

import { useEffect, useRef } from "react";
import { useFocusTrap } from "@/lib/useFocusTrap";

const GROUPS = [
  {
    title: "Navigate",
    items: [
      ["⌘K / Ctrl K", "Command palette"],
      ["1 / 2 / 3 / 4", "Stage / Structure / Ledger / Trace"],
      ["[ / ]", "Previous / next version"],
      ["C", "Compare preview with head"],
      ["B", "Blink head against preview"],
      ["F", "Focus mode"],
      ["?", "This shortcut sheet"],
    ],
  },
  {
    title: "Stage",
    items: [
      ["Click", "Select an element"],
      ["G / R / S", "Move / rotate / scale tool"],
      ["Drag gizmo", "Transform the selected element"],
      ["Drag / scroll", "Orbit / zoom"],
      ["Esc", "Clear selection or close"],
    ],
  },
  {
    title: "Structure & edit",
    items: [
      ["Arrow keys", "Nudge focused node"],
      ["Enter", "Select focused node"],
      ["L", "Lock or unlock selected"],
      ["⌘Z / Ctrl Z", "Undo"],
      ["⇧⌘Z / Ctrl ⇧ Z", "Redo"],
    ],
  },
];

export default function ShortcutOverlay({ open, onClose }: { open: boolean; onClose: () => void }) {
  const dialogRef = useRef<HTMLDivElement>(null);
  useFocusTrap(open, dialogRef);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose, open]);

  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-[130] flex items-start justify-center bg-[#03040a]/75 px-4 pt-[10vh] backdrop-blur-sm"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label="Keyboard shortcuts"
        tabIndex={-1}
        className="w-full max-w-2xl overflow-hidden rounded-2xl border border-white/12 bg-[#0b0d10] shadow-[0_40px_120px_rgba(0,0,0,0.65)]"
      >
        <div className="flex items-center justify-between border-b border-white/8 px-5 py-3">
          <div>
            <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-signal/70">Instrument keys</p>
            <h2 className="mt-0.5 text-base font-medium text-foreground/90">Keyboard shortcuts</h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="inline-flex min-h-9 items-center rounded-md border border-white/10 px-3 text-xs text-foreground/55 hover:text-foreground"
          >
            Close
          </button>
        </div>
        <div className="grid gap-6 p-5 sm:grid-cols-3">
          {GROUPS.map((group) => (
            <section key={group.title}>
              <h3 className="font-mono text-[11px] uppercase tracking-[0.18em] text-foreground/40">{group.title}</h3>
              <dl className="mt-2 space-y-2">
                {group.items.map(([keys, label]) => (
                  <div key={keys}>
                    <dt className="font-mono text-[11px] text-signal/80">{keys}</dt>
                    <dd className="mt-0.5 text-xs text-foreground/55">{label}</dd>
                  </div>
                ))}
              </dl>
            </section>
          ))}
        </div>
        <p className="border-t border-white/8 px-5 py-3 text-xs leading-5 text-foreground/40">
          Shortcuts are ignored while typing in an input, textarea, or editable field. Shortcuts never bypass locks.
        </p>
      </div>
    </div>
  );
}
