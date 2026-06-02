"use client";

interface Template { scenario_id: string; title: string; purpose: string; payload: Record<string, unknown>; }

const GALLERY: Template[] = [
  { scenario_id: "clarity_recovery_custom", title: "Clarity Recovery", purpose: "Low vividness triggers clarity support; recovery increases clarity.",
    payload: { imagina_benchmark_scenario_version: "1.0", scenario_id: "clarity_recovery_custom", title: "Clarity Recovery Custom", scenario_type: "clarity", purpose: "Verify clarity recovery.", checkins: [{ label: "baseline", vividness: 5, stability: 5, effort: 4, fatigue: 2, confidence: 6, discomfort: 1 }, { label: "low", vividness: 3, stability: 4, effort: 5, fatigue: 3, confidence: 4, discomfort: 1 }, { label: "recovery", vividness: 8, stability: 7, effort: 3, fatigue: 2, confidence: 8, discomfort: 1 }], expected_outcomes: { clarity_change: "increase", fog_change: "any", detail_change: "any", motion_change: "any", brightness_change: "any", stability_change: "any", policy_family: ["clarity"], safety_gate: "any" }, pass_criteria: { min_score: 60, required_checks: ["scene_responsiveness"], allow_partial_pass: true }, boundaries: { not_clinical: true, not_bci: true, not_neurofeedback_claim: true, not_mind_reading: true } },
  },
  { scenario_id: "effort_overload_custom", title: "Effort Overload", purpose: "High effort simplifies the scene.", payload: {} },
  { scenario_id: "fatigue_downshift_custom", title: "Fatigue Downshift", purpose: "High fatigue reduces load.", payload: {} },
  { scenario_id: "deepening_custom", title: "Deepening", purpose: "High vividness/confidence deepens scene.", payload: {} },
  { scenario_id: "signal_blocked_custom", title: "Signal Blocked", purpose: "Blocked gate prevents adaptation.", payload: {} },
  { scenario_id: "discomfort_pause_custom", title: "Discomfort Pause", purpose: "High discomfort triggers pause.", payload: {} },
];

interface BGPProps { onSelectTemplate: (payload: Record<string, unknown>) => void; }

export function BenchmarkScenarioGalleryPanel({ onSelectTemplate }: BGPProps) {
  return (
    <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-amber-500/50">
      <div className="text-foreground/40 uppercase tracking-[0.1em]">Scenario Gallery (V39)</div>
      <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto">
        {GALLERY.map(t => (
          <div key={t.scenario_id} className="p-2 rounded bg-surface/30 space-y-1 cursor-pointer hover:bg-surface/50" onClick={() => onSelectTemplate(t.payload)}>
            <div className="text-foreground/60 text-[9px]">{t.title}</div>
            <div className="text-foreground/30 text-[7px]">{t.purpose?.slice(0, 60)}</div>
            <button className="px-2 py-0.5 rounded bg-amber-500/20 border border-amber-500/30 text-amber-300 text-[8px]">Load</button>
          </div>
        ))}
      </div>
      <div className="text-foreground/20 text-[7px]">Templates test symbolic scene adaptation. Not BCI, not neurofeedback validation.</div>
    </div>
  );
}
