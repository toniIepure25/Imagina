"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useFocusTrap } from "@/lib/useFocusTrap";
import type { PlatformCommand } from "./commandTypes";

export default function PlatformCommandPalette({
  open,
  onClose,
  actions,
  label = "IMAGINA command palette",
  placeholder = "Jump to a route, instrument, or boundary…",
}: {
  open: boolean;
  onClose: () => void;
  actions: PlatformCommand[];
  label?: string;
  placeholder?: string;
}) {
  const [query, setQuery] = useState("");
  const [cursor, setCursor] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const dialogRef = useRef<HTMLDivElement>(null);
  useFocusTrap(open, dialogRef);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return actions;
    return actions.filter((action) =>
      `${action.label} ${action.detail} ${action.group} ${action.keywords ?? ""}`.toLowerCase().includes(needle),
    );
  }, [actions, query]);

  useEffect(() => {
    if (!open) return;
    const timer = window.setTimeout(() => inputRef.current?.focus(), 20);
    return () => window.clearTimeout(timer);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose, open]);

  useEffect(() => {
    if (!open) {
      const timer = window.setTimeout(() => {
        setQuery("");
        setCursor(0);
      }, 0);
      return () => window.clearTimeout(timer);
    }
  }, [open]);

  if (!open) return null;

  const moveCursor = (direction: number) => {
    if (!filtered.length) return;
    setCursor((current) => (current + direction + filtered.length) % filtered.length);
  };

  return (
    <div
      className="fixed inset-0 z-[120] flex items-start justify-center bg-[#03040a]/75 px-4 pt-[12vh] backdrop-blur-sm"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label={label}
        tabIndex={-1}
        className="w-full max-w-xl overflow-hidden rounded-2xl border border-white/12 bg-[#090b14] shadow-[0_40px_120px_rgba(0,0,0,0.65)]"
      >
        <div className="flex items-center gap-3 border-b border-white/8 px-4 py-3">
          <span className="mono-label text-accent-glow/70">Go</span>
          <input
            ref={inputRef}
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setCursor(0);
            }}
            onKeyDown={(event) => {
              if (event.key === "ArrowDown") {
                event.preventDefault();
                moveCursor(1);
              } else if (event.key === "ArrowUp") {
                event.preventDefault();
                moveCursor(-1);
              } else if (event.key === "Enter") {
                event.preventDefault();
                const action = filtered[cursor];
                if (action && !action.disabled) {
                  onClose();
                  action.run();
                }
              }
            }}
            placeholder={placeholder}
            aria-label="Search commands"
            role="combobox"
            aria-expanded="true"
            aria-autocomplete="list"
            aria-controls="platform-command-list"
            aria-activedescendant={filtered[cursor] ? `platform-command-${filtered[cursor].id}` : undefined}
            className="min-w-0 flex-1 bg-transparent text-base text-foreground outline-none placeholder:text-foreground/30"
          />
          <kbd className="rounded border border-white/10 bg-white/[0.04] px-1.5 py-0.5 font-mono text-[11px] text-foreground/40">
            esc
          </kbd>
        </div>

        <div id="platform-command-list" role="listbox" aria-label="Commands" className="max-h-[52vh] overflow-y-auto p-2">
          {filtered.length === 0 ? (
            <p className="px-3 py-8 text-center text-sm text-foreground/40">No command matches “{query}”.</p>
          ) : (
            filtered.map((action, index) => (
              <button
                key={action.id}
                id={`platform-command-${action.id}`}
                type="button"
                role="option"
                aria-selected={index === cursor}
                aria-disabled={action.disabled || undefined}
                onMouseEnter={() => setCursor(index)}
                onClick={() => {
                  if (action.disabled) return;
                  onClose();
                  action.run();
                }}
                className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition-colors ${
                  action.disabled
                    ? "cursor-not-allowed opacity-40"
                    : index === cursor
                      ? "bg-accent-glow/[0.08]"
                      : "hover:bg-white/[0.03]"
                }`}
              >
                <span
                  className={`grid h-7 w-7 shrink-0 place-items-center rounded-full border font-mono text-[11px] ${
                    index === cursor ? "border-accent-glow/40 text-accent-glow" : "border-white/10 text-foreground/35"
                  }`}
                  aria-hidden="true"
                >
                  {action.group.slice(0, 1)}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium text-foreground/85">{action.label}</span>
                  <span className="block truncate text-xs text-foreground/45">
                    {action.disabled && action.disabledReason ? action.disabledReason : action.detail}
                  </span>
                </span>
                <span className="shrink-0 font-mono text-[11px] uppercase tracking-[0.12em] text-foreground/30">
                  {action.group}
                </span>
              </button>
            ))
          )}
        </div>

        <div className="flex items-center justify-between border-t border-white/8 px-4 py-2 text-[11px] text-foreground/35">
          <span>↑↓ move · enter open · esc close</span>
          <span className="font-mono">local-only navigation</span>
        </div>
      </div>
    </div>
  );
}
