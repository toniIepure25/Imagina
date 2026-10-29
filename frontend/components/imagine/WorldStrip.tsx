"use client";

import HudLabel from "@/components/system/HudLabel";
import Surface from "@/components/system/Surface";
import type { ImaginePreset } from "@/lib/imagine/presets";

export default function WorldStrip({
  presets,
  activeId,
  onSelect,
  onResample,
}: {
  presets: ImaginePreset[];
  activeId: string | null;
  onSelect: (preset: ImaginePreset) => void;
  onResample: () => void;
}) {
  return (
    <Surface tone="tray" className="p-3">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-baseline gap-2">
          <HudLabel>Worlds</HudLabel>
          <span className="font-mono text-[10px] tabular-nums text-foreground/25">{presets.length}</span>
        </div>
        <button
          type="button"
          onClick={onResample}
          className="min-h-9 font-mono text-[10px] uppercase tracking-[0.16em] text-foreground/35 transition-colors hover:text-lumen-mint"
        >
          Surprise
        </button>
      </div>

      <div className="mt-2.5 flex snap-x gap-2 overflow-x-auto pb-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        {presets.map((preset) => {
          const active = preset.id === activeId;
          return (
            <button
              key={preset.id}
              type="button"
              aria-pressed={active}
              aria-label={`${preset.title} preset`}
              onClick={() => onSelect(preset)}
              className={`group relative h-[86px] w-[148px] shrink-0 snap-start overflow-hidden rounded-sm border text-left transition-all duration-300 ${
                active
                  ? "border-lumen-mint/55 shadow-[0_0_0_1px_rgba(136,240,214,0.18),0_16px_30px_-22px_rgba(136,240,214,0.55)]"
                  : "border-white/[0.08] hover:border-white/20"
              }`}
            >
              <span
                className="absolute inset-0 opacity-80 transition-opacity duration-300 group-hover:opacity-100"
                style={{
                  background: `radial-gradient(120% 100% at 20% 0%, ${preset.preview.via} 0%, ${preset.preview.from} 48%, ${preset.preview.to} 100%)`,
                }}
              />
              <span
                className="absolute inset-x-0 bottom-0 h-12 opacity-70"
                style={{ background: `linear-gradient(to top, ${preset.preview.to}, transparent)` }}
              />
              <span
                className="absolute left-3 top-3 h-1 w-6 rounded-full"
                style={{ background: preset.preview.accent, boxShadow: `0 0 14px ${preset.preview.accent}` }}
              />
              <span className="absolute inset-x-0 bottom-0 p-2.5">
                <span className="block truncate text-[11px] font-medium text-white/90">{preset.title}</span>
                <span className="mt-0.5 block truncate font-mono text-[9px] uppercase tracking-[0.12em] text-white/40">
                  {preset.subtitle}
                </span>
              </span>
              {active ? (
                <span className="absolute right-2.5 top-2.5 font-mono text-[9px] uppercase tracking-[0.14em] text-lumen-mint/90">
                  live
                </span>
              ) : null}
            </button>
          );
        })}
      </div>
    </Surface>
  );
}
