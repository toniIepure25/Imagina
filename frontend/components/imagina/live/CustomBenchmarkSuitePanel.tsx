"use client";

interface ImportedScenario { scenario_id: string; payload?: { title?: string }; }
interface CustomSuite { suite_id: string; suite_name: string; created_at: string; scenario_ids: string[]; }
interface SuiteResult { n_scenarios: number; n_passed: number; pass_rate: number; avg_score: number; overall_verdict: string; }

interface CSPProps {
  importedScenarios: ImportedScenario[];
  suites: CustomSuite[];
  onRunSuite: (sid: string) => void;
  onRefresh: () => void;
}

export function CustomBenchmarkSuitePanel({ importedScenarios, suites, onRunSuite, onRefresh }: CSPProps) {
  return (
    <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-emerald-500/50">
      <div className="flex justify-between">
        <div className="text-foreground/40 uppercase tracking-[0.1em]">Custom Suites (V39)</div>
        <span className="text-foreground/30 text-[8px]">{suites.length} suites, {importedScenarios.length} imports</span>
      </div>
      {suites.length === 0 ? (
        <div className="text-foreground/50">Import scenarios from the Studio, then create a suite.</div>
      ) : (
        <div className="space-y-1 max-h-32 overflow-y-auto">
          {suites.map(s => (
            <div key={s.suite_id} className="flex gap-2 text-[8px] p-1.5 rounded bg-surface/30 items-center">
              <span className="text-foreground/60 flex-1 truncate">{s.suite_name}</span>
              <span className="text-foreground/30">{s.scenario_ids?.length || 0} scenarios</span>
              <button onClick={() => onRunSuite(s.suite_id)} className="px-2 py-0.5 rounded bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 hover:bg-emerald-500/30">Run</button>
            </div>
          ))}
        </div>
      )}
      <button onClick={onRefresh} className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">Refresh</button>
    </div>
  );
}
