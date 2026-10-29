"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useFocusTrap } from "@/lib/useFocusTrap";
import {
  useAnimusCommands,
  type AnimusCommandGroup,
} from "./AnimusCommandRegistry";

type PaletteAction = {
  id: string;
  label: string;
  detail: string;
  group: AnimusCommandGroup;
  keywords?: string;
  disabled?: boolean;
  disabledReason?: string;
  run: () => void;
};

export default function AnimusCommandPalette({
  open,
  sessionId,
  onClose,
}: {
  open: boolean;
  sessionId?: string;
  onClose: () => void;
}) {
  const router = useRouter();
  const { commands } = useAnimusCommands();
  const [query, setQuery] = useState("");
  const [cursor, setCursor] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const dialogRef = useRef<HTMLDivElement>(null);
  useFocusTrap(open, dialogRef);

  const actions = useMemo<PaletteAction[]>(() => {
    const go = (href: string) => () => {
      onClose();
      router.push(href);
    };
    const create: PaletteAction[] = [
      {
        id: "new-scene",
        label: "New scene",
        detail: "Describe an intention and open a fresh studio",
        group: "Create",
        keywords: "start begin imagine studio",
        run: go("/animus"),
      },
    ];
    const session: PaletteAction[] = sessionId
      ? [
          {
            id: "studio",
            label: "Open the studio",
            detail: "Candidate, correction, and convergence workspace",
            group: "Session",
            keywords: "scene edit inspect",
            run: go(`/animus/studio/${sessionId}`),
          },
          {
            id: "practice",
            label: "Practice recall",
            detail: "Object, token, or spatial reconstruction",
            group: "Session",
            keywords: "memory task reconstruction",
            run: go(`/animus/practice/${sessionId}`),
          },
          {
            id: "interview",
            label: "Epistemic interview",
            detail: "Belief probes, abstention, and calibration",
            group: "Session",
            keywords: "confidence belief posterior",
            run: go(`/animus/interview/${sessionId}`),
          },
          {
            id: "observatory",
            label: "Open the observatory",
            detail: "Contrast threshold, provenance, and reliability",
            group: "Session",
            keywords: "threshold sdt evidence provenance",
            run: go(`/animus/observatory/${sessionId}`),
          },
        ]
      : [];
    const explore: PaletteAction[] = [
      {
        id: "imagine",
        label: "Imagine lab",
        detail: "First-person local preview with a signal vector",
        group: "Explore",
        keywords: "first person diffusion scene prompt neuro adaptive",
        run: go("/animus/imagine"),
      },
      {
        id: "worlds",
        label: "Saved worlds",
        detail: "Reopen or branch a world you kept",
        group: "Explore",
        keywords: "library saved scenes",
        run: go("/animus/worlds"),
      },
      {
        id: "profile",
        label: "Behavioural profile",
        detail: "Five separate estimates with evidence counts",
        group: "Explore",
        keywords: "measurement dimensions evidence",
        run: go("/animus/profile"),
      },
      {
        id: "about",
        label: "Scientific boundaries",
        detail: "What is active, experimental, disabled, or unauthorized",
        group: "Explore",
        keywords: "claims limitations ethics",
        run: go("/animus/about"),
      },
    ];
    return [...create, ...session, ...commands, ...explore];
  }, [commands, onClose, router, sessionId]);

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

  if (!open) return null;

  const moveCursor = (direction: number) => {
    if (!filtered.length) return;
    setCursor((current) => (current + direction + filtered.length) % filtered.length);
  };

  return (
    <div
      className="fixed inset-0 z-[120] flex items-start justify-center bg-[#03040a]/70 px-4 pt-[12vh] backdrop-blur-sm"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label="ANIMUS command palette"
        tabIndex={-1}
        className="w-full max-w-xl overflow-hidden rounded-2xl border border-white/12 bg-[#090b14] shadow-[0_40px_120px_rgba(0,0,0,0.65)]"
      >
        <div className="flex items-center gap-3 border-b border-white/8 px-4 py-3">
          <span className="font-mono text-[11px] uppercase tracking-[0.2em] text-accent-glow/60">Go</span>
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
            placeholder="Jump to a studio, instrument, or boundary…"
            aria-label="Search commands"
            role="combobox"
            aria-expanded="true"
            aria-autocomplete="list"
            aria-controls="animus-command-list"
            aria-activedescendant={filtered[cursor] ? `animus-command-${filtered[cursor].id}` : undefined}
            className="min-w-0 flex-1 bg-transparent text-sm text-foreground outline-none placeholder:text-foreground/25"
          />
          <kbd className="rounded border border-white/10 bg-white/[0.04] px-1.5 py-0.5 font-mono text-[11px] text-foreground/35">
            esc
          </kbd>
        </div>

        <div id="animus-command-list" role="listbox" aria-label="Commands" className="max-h-[52vh] overflow-y-auto p-2">
          {filtered.length === 0 ? (
            <p className="px-3 py-8 text-center text-xs text-foreground/35">No command matches “{query}”.</p>
          ) : (
            filtered.map((action, index) => (
              <button
                key={action.id}
                id={`animus-command-${action.id}`}
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
                  className={`grid h-7 w-7 shrink-0 place-items-center rounded-full border text-[11px] font-mono ${
                    index === cursor
                      ? "border-accent-glow/40 text-accent-glow"
                      : "border-white/10 text-foreground/30"
                  }`}
                  aria-hidden="true"
                >
                  {action.group.slice(0, 1)}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-xs font-medium text-foreground/85">{action.label}</span>
                  <span className="block truncate text-[11px] text-foreground/35">
                    {action.disabled && action.disabledReason ? action.disabledReason : action.detail}
                  </span>
                </span>
                <span className="shrink-0 font-mono text-[11px] uppercase tracking-[0.12em] text-foreground/20">
                  {action.group}
                </span>
              </button>
            ))
          )}
        </div>

        <div className="flex items-center justify-between border-t border-white/8 px-4 py-2 text-[11px] text-foreground/25">
          <span>↑↓ move · enter open · esc close</span>
          <span className="font-mono">local-only navigation</span>
        </div>
      </div>
    </div>
  );
}
