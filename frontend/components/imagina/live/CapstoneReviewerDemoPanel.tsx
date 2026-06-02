"use client";

import { useState } from "react";

export function CapstoneReviewerDemoPanel({ onRun, onBuildEvidence, onBuildNarrative, onCheckReadiness }: {
  onRun: () => Promise<Record<string, unknown> | null>;
  onBuildEvidence: () => Promise<unknown>;
  onBuildNarrative: () => Promise<unknown>;
  onCheckReadiness: () => Promise<unknown>;
}) {
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);

  const steps = (result?.steps as unknown[]) || [];
  const verdict = String(result?.overall_verdict || "");
  const summary = String(result?.steps_summary || "");
  const rawEEG = String(result?.raw_eeg_included || "");

  return (
    <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-amber-500/50">
      <div className="flex justify-between">
        <div className="text-foreground/40 uppercase tracking-[0.1em]">Capstone Demo (V44)</div>
        {result && (
          <span className={`px-2 py-0.5 rounded text-[8px] ${verdict === "reviewer_ready" ? "bg-green-500/20 text-green-400" : "bg-amber-500/20 text-amber-400"}`}>
            {verdict}
          </span>
        )}
      </div>
      <div className="text-foreground/30 text-[9px]">Unified pipeline: live demo → scene replay → benchmark → scorecard → scenario SDK → policy matrix → leaderboard → export.</div>
      <button onClick={async () => { setLoading(true); setResult(await onRun()); setLoading(false); }}
        disabled={loading} className="px-4 py-2 rounded bg-amber-500/20 border border-amber-500/30 text-amber-300 hover:bg-amber-500/30 disabled:opacity-50">
        {loading ? "Running..." : "Run Capstone Demo"}
      </button>
      {result && (
        <div className="space-y-1 max-h-48 overflow-y-auto">
          {steps.map((s: unknown, i: number) => {
            const step = s as Record<string, string>;
            return (
              <div key={step.step_id || String(i)} className="flex gap-2 text-[8px] p-1.5 rounded bg-surface/30 items-center">
                <span className={step.status === "passed" ? "text-green-400" : step.status === "skipped" ? "text-amber-400" : "text-red-400"}>
                  {step.status === "passed" ? "✓" : step.status === "skipped" ? "→" : "✕"}
                </span>
                <span className="text-foreground/50 w-24 truncate">{step.name}</span>
                <span className="text-foreground/30 flex-1 truncate">{step.summary}</span>
              </div>
            );
          })}
          <div className="text-foreground/50 text-[9px] pt-1">{summary}</div>
        </div>
      )}
      <div className="flex gap-2">
        <button onClick={onBuildEvidence} className="px-3 py-1.5 rounded bg-violet-500/20 border border-violet-500/30 text-violet-300 hover:bg-violet-500/30">Build Evidence</button>
        <button onClick={onBuildNarrative} className="px-3 py-1.5 rounded bg-cyan-500/20 border border-cyan-500/30 text-cyan-300 hover:bg-cyan-500/30">Narrative</button>
        <button onClick={onCheckReadiness} className="px-3 py-1.5 rounded bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 hover:bg-emerald-500/30">Readiness</button>
      </div>
      <div className="text-foreground/30 text-[8px]">raw_eeg_included: {rawEEG}</div>
      <div className="text-foreground/20 text-[7px]">{String(result?.capstone_boundary || "")}</div>
    </div>
  );
}
