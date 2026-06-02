"use client";

interface Scenario { scenario_id: string; title?: string; origin: string; valid: boolean; quality_score?: number; payload?: { title?: string }; }
interface Suite { suite_id: string; suite_name: string; created_at: string; scenario_ids: string[]; }

export function ImportedScenarioRegistryPanel({ scenarios, onRun, onRemove, onRefresh }: {
  scenarios: Scenario[]; onRun: (sid: string) => void; onRemove: (sid: string) => void; onRefresh: () => void;
}) {
  return (
    <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-cyan-500/50">
      <div className="flex justify-between">
        <div className="text-foreground/40 uppercase tracking-[0.1em]">Imported Scenarios (V38)</div>
        <span className="text-foreground/30 text-[8px]">{scenarios.length} scenarios</span>
      </div>
      {scenarios.length === 0 ? (
        <div className="text-foreground/50">Import one from the Scenario Studio.</div>
      ) : (
        <div className="space-y-1 max-h-48 overflow-y-auto">
          {scenarios.map(s => (
            <div key={s.scenario_id} className="flex gap-2 text-[8px] p-1.5 rounded bg-surface/30 items-center">
              <span className={s.valid ? "text-green-400" : "text-red-400"}>{s.valid ? "✓" : "✕"}</span>
              <span className="text-foreground/60 flex-1 truncate">{s.payload?.title || s.scenario_id || "—"}</span>
              <button onClick={() => onRun(s.scenario_id)} className="px-2 py-0.5 rounded bg-indigo-500/20 border border-indigo-500/30 text-indigo-300 hover:bg-indigo-500/30">Run</button>
              <button onClick={() => onRemove(s.scenario_id)} className="px-2 py-0.5 rounded bg-red-500/20 border border-red-500/30 text-red-400 hover:bg-red-500/30">✕</button>
            </div>
          ))}
        </div>
      )}
      <button onClick={onRefresh} className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">Refresh</button>
    </div>
  );
}

export function CustomBenchmarkSuitePanel({ suites, onRun, onRefresh }: {
  suites: Suite[]; onRun: (sid: string) => void; onRefresh: () => void;
}) {
  return (
    <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-emerald-500/50">
      <div className="flex justify-between">
        <div className="text-foreground/40 uppercase tracking-[0.1em]">Custom Suites (V38)</div>
        <span className="text-foreground/30 text-[8px]">{suites.length}</span>
      </div>
      {suites.length === 0 ? (
        <div className="text-foreground/50">No custom suites yet.</div>
      ) : (
        <div className="space-y-1">
          {suites.map(s => (
            <div key={s.suite_id} className="flex gap-2 text-[8px] p-1.5 rounded bg-surface/30 items-center">
              <span className="text-foreground/60 flex-1 truncate">{s.suite_name}</span>
              <button onClick={() => onRun(s.suite_id)} className="px-2 py-0.5 rounded bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 hover:bg-emerald-500/30">Run</button>
            </div>
          ))}
        </div>
      )}
      <button onClick={onRefresh} className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">Refresh</button>
    </div>
  );
}
