"use client";

import { useState } from "react";
import type { SceneGraph } from "@/lib/animusStudioApi";
import SceneSketch from "./SceneSketch";

const PROMPTS = [
  { id: "keep", label: "What must stay?", hint: "A constraint, a relation, a feeling." },
  { id: "uncertain", label: "What is uncertain?", hint: "A detail you have not decided yet." },
  { id: "surprise", label: "What would surprise you?", hint: "A direction you have not considered." },
];

export default function FirstLookGate({
  scene,
  intention,
  onReveal,
}: {
  scene: SceneGraph;
  intention: string;
  onReveal: () => void;
}) {
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [showPrompts, setShowPrompts] = useState(true);

  return (
    <div
      role="dialog"
      aria-labelledby="first-look-title"
      aria-describedby="first-look-body"
      className="grid min-h-[420px] gap-0 overflow-hidden rounded-lg border border-white/10 bg-[#080a0c] xl:grid-cols-[1.1fr_0.9fr]"
    >
      <div className="relative min-h-[220px] overflow-hidden border-b border-white/8 xl:border-b-0 xl:border-r">
        <SceneSketch scene={scene} className="absolute inset-0 h-full w-full opacity-90" showLabels />
        <div className="absolute inset-0 bg-gradient-to-t from-[#080a0c] via-transparent to-transparent" />
        <div className="absolute left-4 top-4">
          <p className="font-mono text-[11px] uppercase tracking-[0.24em] text-signal/60">Deliberate first look</p>
          <p className="mt-1 max-w-[240px] text-[11px] leading-relaxed text-foreground/45">
            The candidate is hidden until you have written down your own starting point.
          </p>
        </div>
        <p className="absolute bottom-4 left-4 right-4 font-display text-lg leading-snug text-foreground/85">
          “{intention || scene.title}”
        </p>
      </div>

      <div className="flex flex-col p-4 sm:p-5">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-foreground/30">Before the scene appears</p>
          <h1 id="first-look-title" className="mt-1 font-display text-2xl leading-tight text-foreground/90">
            Start from your image, not the candidate.
          </h1>
          <p id="first-look-body" className="mt-2 text-[11px] leading-relaxed text-foreground/40">
            This is not a test and nothing is scored. The notes stay in this browser tab and are not sent anywhere.
            You can skip and reveal the scene at any time.
          </p>
        </div>

        {showPrompts ? (
          <div className="mt-4 space-y-3">
            {PROMPTS.map((prompt) => (
              <label key={prompt.id} className="block">
                <span className="flex items-baseline justify-between gap-2">
                  <span className="text-[11px] text-foreground/65">{prompt.label}</span>
                  <span className="text-[11px] text-foreground/25">{prompt.hint}</span>
                </span>
                <textarea
                  value={answers[prompt.id] ?? ""}
                  onChange={(event) => setAnswers((current) => ({ ...current, [prompt.id]: event.target.value }))}
                  rows={2}
                  className="mt-1 w-full resize-none rounded border border-white/10 bg-white/[0.025] px-2.5 py-1.5 text-[11px] leading-relaxed text-foreground/75 placeholder:text-foreground/20 focus:border-signal/35 focus:outline-none"
                  placeholder="Optional — a few words are enough"
                />
              </label>
            ))}
          </div>
        ) : null}

        <div className="mt-auto flex flex-wrap items-center gap-2 pt-4">
          <button
            type="button"
            onClick={onReveal}
            className="rounded border border-signal/40 bg-signal/10 px-3 py-1.5 text-[11px] text-signal hover:bg-signal/15"
            data-testid="first-look-reveal"
          >
            Reveal the scene
          </button>
          <button
            type="button"
            onClick={() => setShowPrompts((current) => !current)}
            className="rounded border border-white/10 px-2.5 py-1.5 text-[11px] text-foreground/40 hover:text-foreground/70"
          >
            {showPrompts ? "Hide prompts" : "Show prompts"}
          </button>
          <button
            type="button"
            onClick={onReveal}
            className="ml-auto text-[11px] text-foreground/30 underline decoration-white/20 underline-offset-2 hover:text-foreground/60"
          >
            Skip for now
          </button>
        </div>
      </div>
    </div>
  );
}
