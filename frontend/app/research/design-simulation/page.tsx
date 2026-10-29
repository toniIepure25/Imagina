"use client";

import { useState } from "react";
import AppShell from "@/components/layout/AppShell";
import PageHeader from "@/components/platform/PageHeader";
import BoundaryNote from "@/components/platform/BoundaryNote";
import { apiFetch } from "@/lib/api";

const SCENARIOS = [
  { id: "strict_null", label: "Strict null", description: "All conditions identical." },
  { id: "small_adaptive", label: "Small adaptive effect", description: "Small genuine adaptive benefit." },
  { id: "medium_adaptive", label: "Medium adaptive effect", description: "Medium adaptive benefit." },
  { id: "subjective_only", label: "Subjective only", description: "Vividness improves, precision does not." },
  { id: "practice_only", label: "Practice only", description: "All conditions improve equally." },
  { id: "placebo_expectancy", label: "Placebo / expectancy", description: "Self-report affected by condition label." },
  { id: "carryover", label: "Carryover", description: "Adaptive effects persist into later conditions." },
  { id: "differential_dropout", label: "Differential dropout", description: "Low performers drop out more." },
  { id: "perceptual_control_only", label: "Perceptual control only", description: "Motor or perceptual improvement only." },
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

interface RunResponse {
  id: number;
  status: string;
  result?: { results?: SimResult[] };
}

async function pollSimulation(id: number): Promise<RunResponse> {
  for (let attempt = 0; attempt < 10; attempt += 1) {
    const run = await apiFetch<RunResponse>(`/api/research-science/simulations/${id}`);
    if (["completed", "failed", "aborted"].includes(run.status)) return run;
    await new Promise((resolve) => window.setTimeout(resolve, 900));
  }
  return apiFetch<RunResponse>(`/api/research-science/simulations/${id}`);
}

export default function DesignSimulationPage() {
  const [results, setResults] = useState<SimResult[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scenarioId, setScenarioId] = useState("strict_null");
  const [run, setRun] = useState<RunResponse | null>(null);

  const runSimulation = async () => {
    setRunning(true);
    setError(null);
    setResults([]);
    setRun(null);
    try {
      const queued = await apiFetch<RunResponse>("/api/research-science/simulations", {
        method: "POST",
        body: JSON.stringify({ scenario_id: scenarioId, mode: "unit", n_participants: 18, base_seed: 42 }),
      });
      setRun(queued);
      if (queued.status === "completed") {
        setResults(queued.result?.results ?? []);
        return;
      }
      const finished = await pollSimulation(queued.id);
      setRun(finished);
      if (finished.status === "completed") setResults(finished.result?.results ?? []);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Simulation endpoint not available.");
    } finally {
      setRunning(false);
    }
  };

  const selected = SCENARIOS.find((scenario) => scenario.id === scenarioId);

  return (
    <AppShell>
      <div className="mx-auto w-full max-w-6xl space-y-5 px-4 py-8 md:px-6 lg:py-10">
        <PageHeader
          eyebrow="Research console · design"
          title="Design simulation workbench"
          description="Queue a Monte Carlo operating-characteristics run for one scenario. Every number below is synthetic; a favorable simulation is not evidence of human efficacy."
          meta={
            <span className="font-mono text-[11px] uppercase tracking-[0.12em] text-foreground/35">
              synthetic · no human data
            </span>
          }
        />

        <div className="grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
          <section className="rounded-xl border border-white/10 bg-white/[0.025] p-4">
            <p className="mono-label text-foreground/45">Scenario grid</p>
            <h2 className="mt-1 text-lg font-semibold text-foreground">Nine falsification cases</h2>
            <div className="mt-3 grid gap-1.5">
              {SCENARIOS.map((scenario) => (
                <button
                  key={scenario.id}
                  type="button"
                  onClick={() => setScenarioId(scenario.id)}
                  aria-pressed={scenarioId === scenario.id}
                  className={`flex min-h-11 items-start gap-2 rounded-lg border px-3 py-2 text-left transition-colors ${
                    scenarioId === scenario.id
                      ? "border-accent/35 bg-accent/[0.08]"
                      : "border-white/8 bg-black/10 hover:border-white/15"
                  }`}
                >
                  <span className={`mt-1 h-1.5 w-1.5 shrink-0 rounded-full ${scenarioId === scenario.id ? "bg-accent-glow" : "bg-white/20"}`} />
                  <span className="min-w-0">
                    <span className="block text-xs font-medium text-foreground/75">{scenario.label}</span>
                    <span className="mt-0.5 block text-[11px] leading-4 text-foreground/40">{scenario.description}</span>
                  </span>
                </button>
              ))}
            </div>
          </section>

          <div className="space-y-4">
            <section className="rounded-xl border border-white/10 bg-white/[0.025] p-4">
              <p className="mono-label text-foreground/45">Operating characteristics</p>
              <h2 className="mt-1 text-lg font-semibold text-foreground">{selected?.label ?? "Select a scenario"}</h2>
              <p className="mt-1 text-xs leading-5 text-foreground/45">
                Unit mode, 18 participants, seed 42. The request is queued for a local worker; this page does not
                manufacture a result if no worker is running.
              </p>
              <button
                type="button"
                onClick={runSimulation}
                disabled={running}
                className="mt-3 inline-flex min-h-11 items-center rounded-lg bg-accent px-4 text-sm font-medium text-white hover:bg-accent-glow hover:text-background disabled:opacity-50"
              >
                {running ? "Queuing and checking…" : "Queue simulation"}
              </button>

              {error ? (
                <p role="alert" className="mt-3 rounded-lg border border-danger/25 bg-danger/[0.06] px-3 py-2 text-xs text-danger/85">
                  {error}
                </p>
              ) : null}

              {run ? (
                <div className="mt-3 rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-xs leading-5 text-foreground/55">
                  Run <span className="font-mono text-foreground/75">#{run.id}</span> · status{" "}
                  <span className={`font-mono ${run.status === "completed" ? "text-signal" : "text-lock"}`}>{run.status}</span>
                  {run.status === "queued" ? (
                    <span className="mt-1 block text-[11px] text-foreground/35">
                      No worker claimed this run. Start the local simulation worker to produce results.
                    </span>
                  ) : null}
                  {run.status === "failed" ? (
                    <span className="mt-1 block text-[11px] text-danger/70">The worker failed this run; no results are shown.</span>
                  ) : null}
                </div>
              ) : null}
            </section>

            {results.length > 0 ? (
              <section className="rounded-xl border border-white/10 bg-white/[0.025] p-4">
                <h2 className="mono-label text-foreground/45">Results</h2>
                <div className="mt-3 overflow-x-auto">
                  <table className="w-full min-w-[600px] text-left text-xs">
                    <thead>
                      <tr className="border-b border-white/10 font-mono text-[11px] uppercase tracking-[0.1em] text-foreground/40">
                        <th className="py-2 pr-3 font-normal">Scenario</th>
                        <th className="py-2 pr-3 text-right font-normal">Power</th>
                        <th className="py-2 pr-3 text-right font-normal">Type I</th>
                        <th className="py-2 pr-3 text-right font-normal">Bias</th>
                        <th className="py-2 pr-3 text-right font-normal">Coverage</th>
                        <th className="py-2 text-right font-normal">Conv.</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/[0.07]">
                      {results.map((result) => (
                        <tr key={result.scenario_id}>
                          <td className="py-2.5 pr-3 font-mono text-foreground/65">{result.scenario_id}</td>
                          <td className="py-2.5 pr-3 text-right text-foreground/60">
                            {result.power > 0 ? `${(result.power * 100).toFixed(1)}%` : "—"}
                          </td>
                          <td className="py-2.5 pr-3 text-right text-foreground/60">
                            {result.type_i_error > 0 ? `${(result.type_i_error * 100).toFixed(1)}%` : "—"}
                          </td>
                          <td className="py-2.5 pr-3 text-right font-mono text-foreground/60">{result.bias.toFixed(4)}</td>
                          <td className="py-2.5 pr-3 text-right text-foreground/60">{(result.coverage * 100).toFixed(1)}%</td>
                          <td className="py-2.5 text-right text-foreground/60">{(result.convergence_rate * 100).toFixed(0)}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <p className="mt-2 text-[11px] text-foreground/35">
                  Monte Carlo standard error reflects a finite simulation count. Values are not exact.
                </p>
              </section>
            ) : (
              <section className="rounded-xl border border-white/10 bg-white/[0.025] p-4">
                <h2 className="mono-label text-foreground/45">What this table will report</h2>
                <dl className="mt-3 grid grid-cols-2 gap-3 text-xs">
                  {[
                    ["Power", "Probability of detecting the modeled effect."],
                    ["Type I error", "False-positive rate under the null."],
                    ["Bias", "Mean error of the effect estimate."],
                    ["Coverage", "Interval coverage of the true effect."],
                  ].map(([term, definition]) => (
                    <div key={term}>
                      <dt className="text-[11px] font-medium text-foreground/60">{term}</dt>
                      <dd className="mt-0.5 text-[11px] leading-4 text-foreground/40">{definition}</dd>
                    </div>
                  ))}
                </dl>
              </section>
            )}
          </div>
        </div>

        <BoundaryNote>
          Design simulations characterize a statistical procedure under synthetic assumptions. They do not validate
          IMAGINA as a training method, and a single favorable scenario must never be presented as proof.
        </BoundaryNote>
      </div>
    </AppShell>
  );
}
