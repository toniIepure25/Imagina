"use client";

interface ScenarioResult {
  scenario_id: string; passed: boolean; score: number; n_steps: number;
  observed_metrics: Record<string, number>; policy_trace: string[]; state_trace: string[];
  pass_fail_checks: Array<{ check: string; passed: boolean; observed: string }>;
  failure_reasons: string[];
}

interface SuiteResult {
  n_scenarios: number; n_passed: number; pass_rate: number; avg_score: number;
  overall_verdict: string; scenario_results: ScenarioResult[]; scientific_boundary?: string;
}

interface CLProps {
  suite: SuiteResult | null; scenarios: Array<{ scenario_id: string; title: string; purpose: string }>;
  onRunScenario: (sid: string) => void; onRunSuite: () => void; onRefresh: () => void;
}

export function ClosedLoopBenchmarkPanel({ suite, scenarios, onRunScenario, onRunSuite, onRefresh }: CLProps) {
  return (
    <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-indigo-500/50">
      <div className="flex justify-between">
        <div className="text-foreground/40 uppercase tracking-[0.1em]">Closed-Loop Benchmark (V36)</div>
        {suite && <span className={`px-2 py-0.5 rounded text-[8px] ${suite.pass_rate >= 0.8 ? "bg-green-500/20 text-green-400" : "bg-amber-500/20 text-amber-400"}`}>{suite.n_passed}/{suite.n_scenarios} passed</span>}
      </div>

      <div className="space-y-1 max-h-40 overflow-y-auto">
        {scenarios?.map(s => (
          <div key={s.scenario_id} className="flex gap-2 text-[8px] p-1.5 rounded bg-surface/30 items-center">
            <span className="text-foreground/60 flex-1 truncate">{s.title}</span>
            <button onClick={() => onRunScenario(s.scenario_id)} className="px-2 py-0.5 rounded bg-indigo-500/20 border border-indigo-500/30 text-indigo-300 hover:bg-indigo-500/30">Run</button>
          </div>
        ))}
      </div>

      {suite && (
        <div className="space-y-1">
          <div className="text-foreground/50 text-[9px]">Score: {suite.avg_score} · Rate: {(suite.pass_rate * 100).toFixed(0)}% · Verdict: <span className="text-indigo-400">{suite.overall_verdict}</span></div>
          {suite.scenario_results?.slice(0, 3).map(r => (
            <div key={r.scenario_id} className="flex gap-2 text-[8px] p-1 rounded bg-surface/30">
              <span className={r.passed ? "text-green-400" : "text-red-400"}>{r.passed ? "✓" : "✕"}</span>
              <span className="text-foreground/40">{r.scenario_id}</span>
              <span className="text-foreground/30">{r.score}</span>
            </div>
          ))}
        </div>
      )}

      <div className="flex gap-2">
        <button onClick={onRunSuite} className="px-3 py-1.5 rounded bg-indigo-500/20 border border-indigo-500/30 text-indigo-300 hover:bg-indigo-500/30">Run Full Suite</button>
        <button onClick={onRefresh} className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">Refresh</button>
      </div>
      <div className="text-foreground/20 text-[7px]">{suite?.scientific_boundary}</div>
    </div>
  );
}
