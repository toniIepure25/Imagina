"use client";

import AnimusScene from "@/components/animus/AnimusScene";
import type { ContrastTrial } from "@/lib/animusStudioApi";

export default function ContrastPair({
  trial,
  selected,
  onSelect,
  disabled = false,
}: {
  trial: ContrastTrial;
  selected: "a" | "b" | null;
  onSelect: (choice: "a" | "b") => void;
  disabled?: boolean;
}) {
  return (
    <div
      className="grid gap-4 md:grid-cols-2"
      role="group"
      aria-label="Choose the scene that matches the one you saw"
    >
      {trial.options.map((option) => {
        const choice = option.id === "b" ? "b" : "a";
        const active = selected === choice;
        return (
          <div
            key={option.id}
            className={`overflow-hidden rounded-2xl border transition ${
              active
                ? "border-accent-glow/70 ring-2 ring-accent-glow/25"
                : "border-white/10 hover:border-white/20"
            }`}
          >
            <AnimusScene
              scene={option.scene}
              selectedId={null}
              onSelect={() => undefined}
              className="h-[240px]"
              showOverlay={false}
              interactive={false}
            />
            <button
              type="button"
              className={`flex w-full items-center justify-between px-4 py-3 text-left text-sm ${
                active ? "bg-accent-glow/10 text-foreground" : "bg-white/[0.02] text-foreground/75"
              }`}
              aria-pressed={active}
              aria-label={`Choose ${option.label}`}
              onClick={() => onSelect(choice)}
              disabled={disabled}
            >
              <span>{option.label}</span>
              <span className="text-[10px] uppercase tracking-[0.18em] text-foreground/40">
                {active ? "selected" : "choose"}
              </span>
            </button>
          </div>
        );
      })}
    </div>
  );
}
