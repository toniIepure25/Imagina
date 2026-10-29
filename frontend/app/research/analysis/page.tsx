"use client";

import { useState } from "react";
import AppShell from "@/components/layout/AppShell";
import PageHeader from "@/components/platform/PageHeader";
import BoundaryNote from "@/components/platform/BoundaryNote";
import EvidenceMark from "@/components/evidence/EvidenceMark";
import { apiFetch } from "@/lib/api";

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
  inference_valid: boolean;
  primary_estimator_status: string;
}

interface AnalysisRun {
  id: number;
  status: string;
  results?: Record<string, AnalysisResult>;
}

async function pollAnalysis(id: number): Promise<AnalysisRun> {
  for (let attempt = 0; attempt < 10; attempt += 1) {
    const run = await apiFetch<AnalysisRun>(`/api/research-science/analyses/${id}`);
    if (["completed", "failed", "aborted"].includes(run.status)) return run;
    await new Promise((resolve) => window.setTimeout(resolve, 900));
  }
  return apiFetch<AnalysisRun>(`/api/research-science/analyses/${id}`);
}

function primaryResult(run: AnalysisRun): AnalysisResult | null {
  if (!run.results) return null;
  return run.results.primary ?? Object.values(run.results)[0] ?? null;
}

export default function AnalysisPage() {
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [run, setRun] = useState<AnalysisRun | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runAnalysis = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    setRun(null);
    try {
      const queued = await apiFetch<AnalysisRun>("/api/research-science/analyses", {
        method: "POST",
        body: JSON.stringify({ scenario_id: "medium_adaptive", seed: 42, n_participants: 18 }),
      });
      setRun(queued);
      if (queued.status === "completed") {
        setResult(primaryResult(queued));
        return;
      }
      const finished = await pollAnalysis(queued.id);
      setRun(finished);
      if (finished.status === "completed") setResult(primaryResult(finished));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Analysis endpoint not available.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppShell>
      <div className="mx-auto w-full max-w-5xl space-y-5 px-4 py-8 md:px-6 lg:py-10">
        <PageHeader
          eyebrow="Research console · analysis"
          title="Confirmatory analysis workbench"
          description="One pre-specified primary contrast on synthetic data: adaptive versus yoked, on standardized objective reconstruction error. Exploratory output is labeled and never promoted to confirmatory."
          meta={
            <span className="font-mono text-[11px] uppercase tracking-[0.12em] text-foreground/35">
              estimand frozen · no human data
            </span>
          }
        />

        <section className="rounded-xl border border-white/10 bg-white/[0.025] p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="mono-label text-accent-glow/65">Primary estimand</p>
              <h2 className="mt-1 text-lg font-semibold text-foreground">Within-participant ATE</h2>
            </div>
            <code className="rounded border border-white/10 bg-black/25 px-2 py-1 font-mono text-[11px] text-foreground/55">
              adaptive · yoked
            </code>
          </div>
          <p className="mt-2 font-mono text-sm text-foreground/65">
            E[Y(adaptive) − Y(yoked)] on standardized objective imagery reconstruction error
          </p>
          <p className="mt-1 text-xs leading-5 text-foreground/45">
            A negative effect means adaptive produces lower, better reconstruction error. The 8-level curriculum and
            safety monitor are part of the adaptive condition, not separate interventions.
          </p>
        </section>

        <section className="rounded-xl border border-white/10 bg-white/[0.025] p-4">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="mono-label text-foreground/45">Synthetic analysis</p>
              <h2 className="mt-1 text-lg font-semibold text-foreground">Medium adaptive scenario</h2>
              <p className="mt-1 text-[11px] text-foreground/40">18 participants · seed 42 · queued for local worker</p>
            </div>
            <button
              type="button"
              onClick={runAnalysis}
              disabled={loading}
              className="inline-flex min-h-11 items-center rounded-lg bg-accent px-4 text-sm font-medium text-white hover:bg-accent-glow hover:text-background disabled:opacity-50"
            >
              {loading ? "Queuing and checking…" : "Queue analysis"}
            </button>
          </div>

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
                  No worker claimed this run. Start the local analysis worker to produce estimates.
                </span>
              ) : null}
            </div>
          ) : null}

          {result ? (
            <div className="mt-3 space-y-4">
              <div className="flex items-start gap-2 rounded-lg border border-surface-border bg-white/[0.025] p-3">
                <EvidenceMark evidenceId="synthetic.estimate" />
                <p className="text-[11px] leading-5 text-foreground/45">
                  These values come from a synthetic scenario, not human participants. They check the analysis
                  pipeline and cannot support a claim about IMAGINA or a clinical population.
                </p>
              </div>

              <dl className="grid grid-cols-2 gap-3 md:grid-cols-4">
                {[
                  ["Effect estimate", result.effect_estimate.toFixed(4)],
                  ["Standard error", result.standard_error.toFixed(4)],
                  ["95% CI", `[${result.ci_lower.toFixed(4)}, ${result.ci_upper.toFixed(4)}]`],
                  ["p-value", result.p_value < 0.001 ? "<0.001" : result.p_value.toFixed(4)],
                  ["Participants", String(result.n_participants)],
                  ["Trials", String(result.n_trials)],
                  ["Missing", String(result.n_missing)],
                  ["Population", result.analysis_population],
                ].map(([term, value]) => (
                  <div key={term} className="rounded-lg border border-white/8 bg-black/15 p-3">
                    <dt className="text-[11px] text-foreground/40">{term}</dt>
                    <dd className="mt-1 truncate font-mono text-sm text-foreground/75">{value}</dd>
                  </div>
                ))}
              </dl>

              <div className="rounded-lg border border-white/8 bg-black/15 p-3 text-xs leading-6 text-foreground/55">
                <p>
                  <span className="text-foreground/40">Model:</span>{" "}
                  <code className="font-mono text-[11px] text-foreground/65">{result.model_formula}</code>
                </p>
                <p>
                  <span className="text-foreground/40">Converged:</span> {result.converged ? "yes" : "no"} ·{" "}
                  <span className="text-foreground/40">Classification:</span>{" "}
                  {result.is_fallback ? "fallback / exploratory" : "confirmatory"}
                </p>
                {result.singularity_warning ? (
                  <p className="text-lock/80">Singularity warning: random effects may be underestimated.</p>
                ) : null}
              </div>
            </div>
          ) : null}
        </section>

        <section className="rounded-xl border border-white/10 bg-white/[0.025] p-4 text-xs leading-6 text-foreground/45">
          <h2 className="mono-label text-foreground/45">Inference discipline</h2>
          <ul className="mt-2 space-y-1.5">
            <li>· One primary contrast (adaptive versus yoked), with Holm correction for key secondary endpoints.</li>
            <li>· Exploratory analyses are labeled and receive no confirmatory interpretation.</li>
            <li>· A synthetic result is a property of the simulation assumptions, not of IMAGINA in humans.</li>
          </ul>
        </section>

        <BoundaryNote>
          This workbench runs statistical machinery on synthetic data. It does not establish human efficacy, a
          neuroscientific mechanism, or a clinical benefit.
        </BoundaryNote>
      </div>
    </AppShell>
  );
}
