"use client";

import { useState } from "react";
import AppShell from "@/components/layout/AppShell";

const SCENARIOS = [
  { id: "strict_null", label: "Strict Null", description: "All conditions identical" },
  { id: "small_adaptive", label: "Small Adaptive Effect", description: "Small genuine adaptive benefit" },
  { id: "medium_adaptive", label: "Medium Adaptive Effect", description: "Medium adaptive benefit" },
  { id: "subjective_only", label: "Subjective-Only", description: "Vividness improves, precision does not" },
  { id: "practice_only", label: "Practice-Only", description: "All conditions improve equally" },
  { id: "placebo_expectancy", label: "Placebo/Expectancy", description: "Self-report affected by condition label" },
  { id: "carryover", label: "Carryover", description: "Adaptive effects persist into later conditions" },
  { id: "differential_dropout", label: "Differential Dropout", description: "Low performers drop out more" },
  { id: "perceptual_control_only", label: "Perceptual Control Only", description: "Motor/perceptual improvement only" },
];

interface SimResult {
  scenario_id: string;
  power: number;
  power_se: number;
  type_i_error: number;
  type_i_se: number;
  bias: number;
  rmse: number;
  coverage: number;
  coverage_se: number;
  convergence_rate: number;
  fallback_rate: number;
  valid_inference_rate: number;
  negative_control_fp_rate: number;
  oracle_effect: number;
  oracle_se: number;
  n_iterations: number;
  mode: string;
}

export default function DesignSimulationPage() {
  const [results, setResults] = useState<SimResult[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runSimulation = async () => {
    setRunning(true);
    setError(null);
    try {
      const res = await fetch("/api/research/simulation/run", { method: "POST" });
      if (!res.ok) {
        setError(`Simulation API returned ${res.status}`);
        return;
      }
      const data = await res.json();
      if (data.results) {
        setResults(Object.values(data.results));
      }
    } catch {
      setError("Simulation endpoint not available. Results shown from last run.");
    } finally {
      setRunning(false);
    }
  };

  return (
    <AppShell>
      <div className="max-w-5xl mx-auto space-y-8 p-6">
        <div className="bg-amber-50 border border-amber-300 rounded-lg p-4 text-sm text-amber-900">
          <strong>Research Disclaimer:</strong> Synthetic engineering and statistical
          validation only. No human efficacy or neuroscientific claim.
          Do not present a single favorable simulation as proof.
        </div>

        <h1 className="text-2xl font-bold">Design Simulation Workbench</h1>

        <section>
          <h2 className="text-xl font-semibold mb-3">Scenario Grid</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {SCENARIOS.map((s) => (
              <div key={s.id} className="border rounded-lg p-3 bg-white">
                <span className="font-medium text-sm">{s.label}</span>
                <p className="text-xs text-gray-500 mt-1">{s.description}</p>
              </div>
            ))}
          </div>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-3">Operating Characteristics</h2>
          <button
            onClick={runSimulation}
            disabled={running}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 text-sm mb-4"
          >
            {running ? "Running..." : "Run Simulation (fast mode)"}
          </button>

          {error && <p className="text-sm text-amber-600 mb-2">{error}</p>}

          {results.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm border-collapse">
                <thead>
                  <tr className="bg-gray-100">
                    <th className="text-left p-2 border">Scenario</th>
                    <th className="text-right p-2 border">Power</th>
                    <th className="text-right p-2 border">Type I</th>
                    <th className="text-right p-2 border">Bias</th>
                    <th className="text-right p-2 border">RMSE</th>
                    <th className="text-right p-2 border">Coverage</th>
                    <th className="text-right p-2 border">Convergence</th>
                    <th className="text-right p-2 border">Iterations</th>
                  </tr>
                </thead>
                <tbody>
                  {results.map((r) => (
                    <tr key={r.scenario_id} className="hover:bg-gray-50">
                      <td className="p-2 border font-mono text-xs">{r.scenario_id}</td>
                      <td className="p-2 border text-right">
                        {r.power > 0 ? `${(r.power * 100).toFixed(1)}% ±${(r.power_se * 100).toFixed(1)}` : "—"}
                      </td>
                      <td className="p-2 border text-right">
                        {r.type_i_error > 0 ? `${(r.type_i_error * 100).toFixed(1)}% ±${(r.type_i_se * 100).toFixed(1)}` : "—"}
                      </td>
                      <td className="p-2 border text-right">{r.bias.toFixed(4)}</td>
                      <td className="p-2 border text-right">{r.rmse.toFixed(4)}</td>
                      <td className="p-2 border text-right">{(r.coverage * 100).toFixed(1)}%</td>
                      <td className="p-2 border text-right">{(r.convergence_rate * 100).toFixed(0)}%</td>
                      <td className="p-2 border text-right">{r.n_iterations}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="text-xs text-gray-500 mt-2">
                Monte Carlo SE reflects finite simulation count. Values are not exact.
              </p>
            </div>
          )}
        </section>
      </div>
    </AppShell>
  );
}
