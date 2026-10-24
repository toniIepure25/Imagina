"use client";

import Button from "@/components/common/Button";
import type { EpistemicProbe as EpistemicProbeData } from "@/lib/animusStudioApi";

interface EpistemicProbeProps {
  probe: EpistemicProbeData;
  selected: string | null;
  confidence: number;
  abstained: boolean;
  busy: boolean;
  onSelect: (choice: string) => void;
  onConfidence: (confidence: number) => void;
  onAbstain: (abstained: boolean) => void;
  onSubmit: () => void;
}

export default function EpistemicProbe({
  probe,
  selected,
  confidence,
  abstained,
  busy,
  onSelect,
  onConfidence,
  onAbstain,
  onSubmit,
}: EpistemicProbeProps) {
  const canSubmit = !busy && (abstained || Boolean(selected));

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-[10px] uppercase tracking-[0.18em] text-accent-glow/65">
          {probe.probe_type === "spatial_relation" ? "Spatial relation" : "Object presence"}
          {" · "}
          difficulty {Math.round(probe.difficulty * 100)}%
        </span>
        <span className="text-[11px] text-foreground/35">Binary probe · no target reveal</span>
      </div>
      <h2 className="mt-2 text-xl font-medium tracking-tight">{probe.prompt}</h2>

      <div className="mt-5 grid gap-3">
        {probe.options.map((option) => (
          <button
            key={option.id}
            type="button"
            aria-pressed={selected === option.id && !abstained}
            onClick={() => {
              onAbstain(false);
              onSelect(option.id);
            }}
            className={`rounded-xl border px-4 py-3 text-left text-sm transition ${
              selected === option.id && !abstained
                ? "border-accent-glow/70 bg-accent-glow/[0.08] text-foreground"
                : "border-white/10 text-foreground/70 hover:border-white/25"
            }`}
          >
            <span className="mr-3 text-[10px] uppercase tracking-wide text-foreground/35">
              {option.id}
            </span>
            {option.label}
          </button>
        ))}
      </div>

      <button
        type="button"
        aria-pressed={abstained}
        onClick={() => onAbstain(!abstained)}
        className={`mt-3 w-full rounded-xl border px-4 py-3 text-left text-sm transition ${
          abstained
            ? "border-amber-300/45 bg-amber-300/[0.06] text-amber-100/80"
            : "border-white/10 text-foreground/55 hover:border-white/25"
        }`}
      >
        I am not sure enough to answer
        <span className="mt-1 block text-[11px] text-foreground/35">
          An abstention is recorded as coverage, not as a wrong answer.
        </span>
      </button>

      <div className={`mt-6 rounded-xl border border-white/10 bg-white/[0.025] p-4 ${abstained ? "opacity-50" : ""}`}>
        <div className="flex items-center justify-between gap-4">
          <label htmlFor="epistemic-confidence" className="text-xs text-foreground/55">
            How confident are you in this answer?
          </label>
          <span className="text-sm tabular-nums text-foreground/70">{confidence}%</span>
        </div>
        <input
          id="epistemic-confidence"
          type="range"
          min={50}
          max={100}
          step={5}
          value={confidence}
          disabled={abstained || busy}
          onChange={(event) => onConfidence(Number(event.target.value))}
          className="mt-3 w-full accent-[#8ea2ff]"
        />
        <p className="mt-2 text-[11px] text-foreground/35">
          Confidence is stored separately from accuracy. A confident error and a low-confidence error
          are different observations.
        </p>
      </div>

      <Button className="mt-5 w-full" onClick={onSubmit} disabled={!canSubmit}>
        {busy ? "Recording locally…" : abstained ? "Record abstention" : "Record answer"}
      </Button>
    </div>
  );
}
