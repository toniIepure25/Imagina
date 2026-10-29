"use client";

import { useMemo, useState } from "react";
import type { PracticeLayout, PracticePlacement, PracticeToken } from "@/lib/animusStudioApi";

interface ReconstructionBoardProps {
  mode: "select" | "place";
  tokens: PracticeToken[];
  layout?: PracticeLayout | null;
  selectedTokenIds: string[];
  placements: PracticePlacement[];
  disabled?: boolean;
  onToggle?: (tokenId: string) => void;
  onPlace?: (tokenId: string, x: number, z: number) => void;
  onClearPlacements?: () => void;
}

function gridSize(layout?: PracticeLayout | null): number {
  return Math.max(3, Math.min(9, Math.round(layout?.grid ?? 7)));
}

function coordinate(index: number, grid: number): number {
  if (grid <= 1) return 0;
  return Math.round((-1 + (index / (grid - 1)) * 2) * 1000) / 1000;
}

function cellIndex(value: number, grid: number): number {
  if (grid <= 1) return 0;
  return Math.max(0, Math.min(grid - 1, Math.round(((value + 1) / 2) * (grid - 1))));
}

function swatch(color?: string | null): string {
  return color && /^#[0-9a-f]{6}$/i.test(color) ? color : "#8ea2ff";
}

export default function ReconstructionBoard({
  mode,
  tokens,
  layout,
  selectedTokenIds,
  placements,
  disabled = false,
  onToggle,
  onPlace,
  onClearPlacements,
}: ReconstructionBoardProps) {
  const [activeTokenOverride, setActiveTokenOverride] = useState<string | null>(null);
  const grid = gridSize(layout);
  const fallbackToken = tokens.find(
    (token) => !placements.some((placement) => placement.token_id === token.token_id),
  ) ?? tokens[0] ?? null;
  const activeToken = tokens.find((token) => token.token_id === activeTokenOverride) ?? fallbackToken;
  const activeTokenId = activeToken?.token_id ?? null;

  const placedByCell = useMemo(() => {
    const map = new Map<string, PracticeToken[]>();
    for (const placement of placements) {
      const token = tokens.find((item) => item.token_id === placement.token_id);
      if (!token) continue;
      const key = `${cellIndex(placement.x, grid)}:${cellIndex(placement.z, grid)}`;
      map.set(key, [...(map.get(key) ?? []), token]);
    }
    return map;
  }, [grid, placements, tokens]);

  if (mode === "select") {
    return (
      <div className="mt-5">
        <p className="text-xs text-foreground/45">
          Select every object you remember. Decoys are present; do not select an object just because it looks
          plausible.
        </p>
        <div role="group" aria-label="Object tokens" className="mt-3 grid gap-2 sm:grid-cols-2">
          {tokens.map((token) => {
            const selected = selectedTokenIds.includes(token.token_id);
            return (
              <button
                key={token.token_id}
                type="button"
                aria-pressed={selected}
                disabled={disabled}
                onClick={() => onToggle?.(token.token_id)}
                className={`flex items-center gap-3 rounded-xl border px-3 py-3 text-left transition disabled:opacity-50 ${
                  selected
                    ? "border-accent-glow/70 bg-accent-glow/[0.08]"
                    : "border-white/10 bg-white/[0.02] hover:border-white/25"
                }`}
              >
                <span
                  aria-hidden="true"
                  className="h-3 w-3 shrink-0 rounded-full border border-white/20"
                  style={{ backgroundColor: swatch(token.color) }}
                />
                <span className="min-w-0">
                  <span className="block truncate text-sm text-foreground/85">{token.label}</span>
                  <span className="mt-0.5 block text-[11px] uppercase tracking-wide text-foreground/35">
                    {token.role} · {token.kind}
                  </span>
                </span>
                <span className="ml-auto text-[11px] uppercase tracking-wide text-foreground/40">
                  {selected ? "Selected" : "Add"}
                </span>
              </button>
            );
          })}
        </div>
        <p aria-live="polite" className="mt-2 text-[11px] text-foreground/35">
          {selectedTokenIds.length} selected
        </p>
      </div>
    );
  }

  return (
    <div className="mt-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs text-foreground/45">
          Pick an object, then choose its position. The grid hides the target layout.
        </p>
        {placements.length ? (
          <button
            type="button"
            onClick={onClearPlacements}
            className="rounded-lg border border-white/10 px-2.5 py-1 text-[11px] uppercase tracking-wide text-foreground/45 transition hover:border-white/25 hover:text-foreground/70"
          >
            Clear placements
          </button>
        ) : null}
      </div>

      <div role="group" aria-label="Objects to place" className="mt-3 flex flex-wrap gap-2">
        {tokens.map((token) => {
          const placed = placements.some((placement) => placement.token_id === token.token_id);
          const active = token.token_id === activeTokenId;
          return (
            <button
              key={token.token_id}
              type="button"
              aria-pressed={active}
              disabled={disabled}
              onClick={() => setActiveTokenOverride(token.token_id)}
              className={`flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs transition disabled:opacity-50 ${
                active
                  ? "border-accent-glow/70 bg-accent-glow/[0.1] text-foreground"
                  : "border-white/10 text-foreground/60 hover:border-white/25"
              }`}
            >
              <span
                aria-hidden="true"
                className="h-2.5 w-2.5 rounded-full border border-white/20"
                style={{ backgroundColor: swatch(token.color) }}
              />
              {token.label}
              <span className="text-[11px] uppercase tracking-wide text-foreground/35">
                {placed ? "placed" : "place"}
              </span>
            </button>
          );
        })}
      </div>

      <div className="mt-4 rounded-xl border border-white/10 bg-[#050810] p-3">
        <div
          role="group"
          aria-label="Spatial layout board"
          className="grid gap-1"
          style={{ gridTemplateColumns: `repeat(${grid}, minmax(0, 1fr))` }}
        >
          {Array.from({ length: grid * grid }, (_, index) => {
            const row = Math.floor(index / grid);
            const column = index % grid;
            const occupants = placedByCell.get(`${column}:${row}`) ?? [];
            const label = activeToken
              ? `Place ${activeToken.label} at row ${row + 1}, column ${column + 1}`
              : `Cell row ${row + 1}, column ${column + 1}`;
            return (
              <button
                key={`${row}-${column}`}
                type="button"
                aria-label={label}
                disabled={disabled || !activeToken}
                onClick={() => {
                  if (!activeToken) return;
                  onPlace?.(activeToken.token_id, coordinate(column, grid), coordinate(row, grid));
                  setActiveTokenOverride(null);
                }}
                className={`flex aspect-square min-h-9 flex-col items-center justify-center overflow-hidden rounded-md border p-0.5 text-center transition disabled:opacity-40 ${
                  occupants.length
                    ? "border-accent-glow/30 bg-accent-glow/[0.07]"
                    : "border-white/[0.06] bg-white/[0.015] hover:border-white/20"
                }`}
              >
                {occupants.map((token) => (
                  <span
                    key={token.token_id}
                    className="w-full truncate text-[11px] leading-tight text-foreground/65 sm:text-[11px]"
                  >
                    {token.label}
                  </span>
                ))}
              </button>
            );
          })}
        </div>
      </div>
      <p aria-live="polite" className="mt-2 text-[11px] text-foreground/35">
        {placements.length} of {tokens.length} objects placed
        {activeToken ? ` · next: ${activeToken.label}` : ""}
      </p>
    </div>
  );
}
