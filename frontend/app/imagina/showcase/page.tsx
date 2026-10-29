"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/layout/AppShell";
import PageHeader from "@/components/platform/PageHeader";
import AsyncState from "@/components/platform/AsyncState";
import BoundaryNote from "@/components/platform/BoundaryNote";
import { apiFetch } from "@/lib/api";

interface Showcase {
  project_title: string;
  tagline: string;
  hero_summary: string;
  architecture_modules: string[];
  demo_flow: string[];
  latest_protocol: { title: string; completed_blocks: number };
  latest_run: { completion_rate: number };
  benchmark_summary: { avg_iqi_proxy: number; avg_fatigue: number };
  scene_replay_summary: { n_frames: number; clarity_change: number };
  skill_progress_summary: { n_total_sessions: number };
  sdk_summary: { schema_version: string };
  manifest: { protocol_hash: string };
  safe_claims: string[];
  forbidden_claims: string[];
  how_to_run: string[];
  reviewer_checklist: string[];
  scientific_boundary?: string;
  visualization_boundary?: string;
}

const RUN_COMMAND = "cd backend && python3 -m app.cli.imagina_demo full";

export default function ShowcasePage() {
  const [showcase, setShowcase] = useState<Showcase | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    apiFetch<Showcase>("/api/imagina/showcase/demo_user", { signal: controller.signal })
      .then((data) => {
        setShowcase(data);
        setError(null);
      })
      .catch((caught: unknown) => {
        if (caught instanceof DOMException && caught.name === "AbortError") return;
        setError(caught instanceof Error ? caught.message : "The showcase endpoint is unavailable.");
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, []);

  async function copyCommand() {
    try {
      await navigator.clipboard.writeText(RUN_COMMAND);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopied(false);
    }
  }

  return (
    <AppShell>
      <div className="mx-auto w-full max-w-5xl space-y-5 px-4 py-8 md:px-6">
        <PageHeader
          eyebrow="Lab · showcase"
          title={showcase?.project_title ?? "Protocol showcase"}
          description={showcase?.tagline ?? "Local-first mental imagery protocol lab and benchmark SDK."}
          actions={
            <button
              type="button"
              onClick={copyCommand}
              className="inline-flex min-h-9 items-center rounded-lg border border-white/12 px-3 font-mono text-[11px] text-foreground/55 hover:text-foreground"
            >
              {copied ? "Copied command" : "Copy seed command"}
            </button>
          }
        />

        {loading ? (
          <AsyncState kind="loading" title="Reading showcase manifest" body="Loading local protocol, benchmark, and scene replay summaries." />
        ) : error ? (
          <AsyncState
            kind="error"
            title="Showcase unavailable"
            body={`${error} The local backend may be offline, or the showcase data has not been seeded.`}
            action={
              <code className="rounded border border-white/10 bg-black/30 px-3 py-2 font-mono text-[11px] text-foreground/60">
                {RUN_COMMAND}
              </code>
            }
          />
        ) : !showcase ? (
          <AsyncState
            kind="empty"
            title="Showcase data not seeded"
            body="Run the local demo bootstrap, then refresh this page. Nothing is sent off this machine."
            action={
              <button
                type="button"
                onClick={copyCommand}
                className="inline-flex min-h-10 items-center rounded-lg border border-white/15 px-4 text-sm text-foreground/70 hover:text-foreground"
              >
                {copied ? "Copied" : "Copy seed command"}
              </button>
            }
          />
        ) : (
          <>
            <p className="max-w-3xl text-sm leading-7 text-foreground/60">{showcase.hero_summary}</p>

            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {[
                ["Protocol", showcase.latest_protocol?.title || "—"],
                ["Completion", `${((showcase.latest_run?.completion_rate ?? 0) * 100).toFixed(0)}%`],
                ["Avg IQI proxy", showcase.benchmark_summary?.avg_iqi_proxy?.toFixed(2) ?? "—"],
                ["Scene frames", String(showcase.scene_replay_summary?.n_frames ?? "—")],
              ].map(([label, value]) => (
                <div key={label} className="rounded-lg border border-white/10 bg-white/[0.025] p-3">
                  <p className="font-mono text-[11px] uppercase tracking-[0.12em] text-foreground/40">{label}</p>
                  <p className="mt-1 truncate text-sm text-foreground/75">{value}</p>
                </div>
              ))}
            </div>

            <section className="rounded-lg border border-white/10 bg-white/[0.025] p-4">
              <h2 className="mono-label text-foreground/45">Architecture</h2>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {showcase.architecture_modules?.map((module) => (
                  <span key={module} className="rounded-full border border-accent/20 bg-accent/[0.06] px-2 py-0.5 font-mono text-[11px] text-accent-glow/80">
                    {module}
                  </span>
                ))}
              </div>
            </section>

            <div className="grid gap-4 md:grid-cols-2">
              <section className="rounded-lg border border-white/10 bg-white/[0.025] p-4">
                <h2 className="mono-label text-foreground/45">Demo flow</h2>
                <ol className="mt-2 space-y-1.5">
                  {showcase.demo_flow?.map((step, index) => (
                    <li key={step} className="flex gap-2 text-xs leading-5 text-foreground/60">
                      <span className="font-mono text-[11px] text-foreground/30">{String(index + 1).padStart(2, "0")}</span>
                      {step}
                    </li>
                  ))}
                </ol>
              </section>

              <section className="rounded-lg border border-white/10 bg-white/[0.025] p-4">
                <h2 className="mono-label text-foreground/45">How to run locally</h2>
                <div className="mt-2 space-y-1.5">
                  {showcase.how_to_run?.map((command) => (
                    <code key={command} className="block rounded border border-white/8 bg-black/25 px-2 py-1 font-mono text-[11px] leading-5 text-foreground/55">
                      {command}
                    </code>
                  ))}
                </div>
              </section>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <section className="rounded-lg border border-signal/20 bg-signal/[0.04] p-4">
                <h2 className="mono-label text-signal/75">Safe claims</h2>
                <ul className="mt-2 space-y-1.5 text-xs leading-5 text-foreground/60">
                  {showcase.safe_claims?.map((claim) => (
                    <li key={claim}>✓ {claim}</li>
                  ))}
                </ul>
              </section>
              <section className="rounded-lg border border-lock/25 bg-lock/[0.05] p-4">
                <h2 className="mono-label text-lock/75">Forbidden claims</h2>
                <ul className="mt-2 space-y-1.5 text-xs leading-5 text-foreground/55">
                  {showcase.forbidden_claims?.map((claim) => (
                    <li key={claim}>✕ {claim}</li>
                  ))}
                </ul>
              </section>
            </div>

            <section className="rounded-lg border border-white/10 bg-white/[0.025] p-4">
              <h2 className="mono-label text-foreground/45">Reviewer checklist</h2>
              <ul className="mt-2 grid gap-1.5 sm:grid-cols-2">
                {showcase.reviewer_checklist?.map((item) => (
                  <li key={item} className="text-xs leading-5 text-foreground/60">
                    · {item}
                  </li>
                ))}
              </ul>
            </section>

            <BoundaryNote>
              {showcase.scientific_boundary || showcase.visualization_boundary || "This showcase reports local engineering evidence, not validated neural decoding or clinical benefit."}
            </BoundaryNote>
          </>
        )}
      </div>
    </AppShell>
  );
}
