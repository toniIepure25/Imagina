"use client";

import { useState } from "react";
import AppShell from "@/components/layout/AppShell";

interface AnalysisResult {
  estimand_id: string;
  model_formula: string;
  model_type: string;
  effect_estimate: number;
  standard_error: number;
  ci_lower: number;
  ci_upper: number;
  test_statistic: number;
  p_value: number;
  standardized_effect: number;
  converged: boolean;
  singularity_warning: boolean;
  n_participants: number;
  n_trials: number;
  n_missing: number;
  analysis_population: string;
  is_fallback: boolean;
}

export default function AnalysisPage() {
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runAnalysis = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/research/analysis/run", { method: "POST" });
      if (!res.ok) {
        setError(`Analysis API returned ${res.status}`);
        return;
      }
      const data = await res.json();
      setResult(data.primary || data);
    } catch {
      setError("Analysis endpoint not available.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppShell>
      <div className="max-w-5xl mx-auto space-y-8 p-6">
        <div className="bg-amber-50 border border-amber-300 rounded-lg p-4 text-sm text-amber-900">
          <strong>Research Disclaimer:</strong> Synthetic engineering and statistical
          validation only. No human efficacy or neuroscientific claim.
        </div>

        <h1 className="text-2xl font-bold">Analysis Workbench</h1>

        <section>
          <h2 className="text-xl font-semibold mb-3">Primary Estimand</h2>
          <div className="border rounded-lg p-4 bg-white space-y-2">
            <p className="text-sm">
              <strong>Estimand:</strong> Within-participant ATE of adaptive vs. yoked on
              standardized objective imagery reconstruction error
            </p>
            <p className="text-sm font-mono">
              E[Y(adaptive) - Y(yoked)]
            </p>
            <p className="text-sm text-gray-600">
              Negative effect = adaptive produces lower (better) error
            </p>
          </div>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-3">Confirmatory Analysis</h2>
          <button
            onClick={runAnalysis}
            disabled={loading}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 text-sm mb-4"
          >
            {loading ? "Running..." : "Run Analysis on Synthetic Data"}
          </button>

          {error && <p className="text-sm text-amber-600">{error}</p>}

          {result && (
            <div className="border rounded-lg p-4 bg-white space-y-4">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <span className="text-gray-500">Effect Estimate</span>
                  <p className="font-mono font-bold">{result.effect_estimate.toFixed(4)}</p>
                </div>
                <div>
                  <span className="text-gray-500">SE</span>
                  <p className="font-mono">{result.standard_error.toFixed(4)}</p>
                </div>
                <div>
                  <span className="text-gray-500">95% CI</span>
                  <p className="font-mono">[{result.ci_lower.toFixed(4)}, {result.ci_upper.toFixed(4)}]</p>
                </div>
                <div>
                  <span className="text-gray-500">p-value</span>
                  <p className="font-mono">{result.p_value < 0.001 ? "<0.001" : result.p_value.toFixed(4)}</p>
                </div>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm border-t pt-3">
                <div>
                  <span className="text-gray-500">Participants</span>
                  <p>{result.n_participants}</p>
                </div>
                <div>
                  <span className="text-gray-500">Trials</span>
                  <p>{result.n_trials}</p>
                </div>
                <div>
                  <span className="text-gray-500">Population</span>
                  <p>{result.analysis_population}</p>
                </div>
              </div>

              <div className="text-sm border-t pt-3 space-y-1">
                <p><strong>Model:</strong> <code className="text-xs bg-gray-100 px-1 py-0.5 rounded">{result.model_formula}</code></p>
                <p><strong>Converged:</strong> {result.converged ? "Yes" : "No"}</p>
                <p><strong>Classification:</strong> {result.is_fallback ? "Fallback (exploratory)" : "Confirmatory"}</p>
                {result.singularity_warning && (
                  <p className="text-amber-600">Singularity warning — random effects may be underestimated</p>
                )}
              </div>
            </div>
          )}
        </section>

        <section className="text-xs text-gray-500 space-y-1">
          <p>Confirmatory analysis: one primary contrast (adaptive vs. yoked) with Holm correction for key secondary.</p>
          <p>Exploratory analyses are labeled as such and do not receive confirmatory interpretation.</p>
        </section>
      </div>
    </AppShell>
  );
}
