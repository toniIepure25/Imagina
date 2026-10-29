"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/layout/AppShell";
import PageHeader from "@/components/platform/PageHeader";
import BoundaryNote from "@/components/platform/BoundaryNote";
import { apiFetch } from "@/lib/api";

interface RegistryData {
  endpoints: Record<string, { id: string; domain: string; role: string; direction: string; objective: boolean; version: string }>;
  hash: string;
}

const CONSTRUCTS = [
  { name: "Imagery precision", domain: "imagery_precision", objective: true, description: "How accurately imagined visual features can be reconstructed." },
  { name: "Imagery control", domain: "imagery_control", objective: true, description: "How accurately a person can intentionally manipulate a represented feature." },
  { name: "Imagery stability", domain: "imagery_stability", objective: true, description: "How consistently the representation is maintained across a delay." },
  { name: "Metacognitive calibration", domain: "metacognitive_calibration", objective: true, description: "Correspondence between confidence and objective correctness." },
  { name: "Subjective vividness", domain: "subjective_vividness", objective: false, description: "Self-reported imagery vividness, secondary construct only." },
  { name: "Perceptual / motor control", domain: "perceptual_motor_control", objective: true, description: "Negative control: perceptual matching with the target visible." },
];

const TASK_BATTERY = [
  { family: "Feature reconstruction", id: "feature_reconstruction", description: "Fixation → target → mask → imagery → reconstruct → confidence." },
  { family: "Imagery manipulation", id: "imagery_manipulation", description: "Base stimulus → mental transform → reconstruct transformed target." },
  { family: "Delayed imagery", id: "delayed_imagery", description: "Multiple retention delays, immediate versus delayed reconstruction." },
  { family: "Perceptual control", id: "perceptual_control", description: "Target visible during matching; isolates motor and perceptual skill." },
];

const ENDPOINTS = [
  { id: "composite_reconstruction_error", role: "primary", objective: true, direction: "lower_is_better", version: "1.0" },
  { id: "orientation_reconstruction_error", role: "key_secondary", objective: true, direction: "lower_is_better", version: "1.0" },
  { id: "hue_reconstruction_error", role: "key_secondary", objective: true, direction: "lower_is_better", version: "1.0" },
  { id: "imagery_manipulation_accuracy", role: "key_secondary", objective: true, direction: "lower_is_better", version: "1.0" },
  { id: "delayed_stability_degradation", role: "key_secondary", objective: true, direction: "lower_is_better", version: "1.0" },
  { id: "metacognitive_calibration", role: "key_secondary", objective: true, direction: "higher_is_better", version: "1.0" },
  { id: "subjective_vividness", role: "subjective_secondary", objective: false, direction: "higher_is_better", version: "1.0" },
  { id: "perceptual_matching_error", role: "negative_control", objective: true, direction: "lower_is_better", version: "1.0" },
  { id: "simple_motor_latency", role: "negative_control", objective: true, direction: "lower_is_better", version: "1.0" },
];

const ROLE_STYLES: Record<string, string> = {
  primary: "border-signal/25 bg-signal/[0.07] text-signal/85",
  key_secondary: "border-accent/25 bg-accent/[0.07] text-accent-glow/85",
  subjective_secondary: "border-white/10 bg-white/[0.03] text-foreground/50",
  negative_control: "border-lock/25 bg-lock/[0.07] text-lock/85",
};

export default function MeasurementPage() {
  const [registry, setRegistry] = useState<RegistryData | null>(null);
  const [registryError, setRegistryError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    apiFetch<RegistryData>("/api/research-science/endpoint-registry", { signal: controller.signal })
      .then((data) => {
        setRegistry(data);
        setRegistryError(null);
      })
      .catch((caught: unknown) => {
        if (caught instanceof DOMException && caught.name === "AbortError") return;
        setRegistryError("Endpoint registry API unavailable; static definitions are shown.");
      });
    return () => controller.abort();
  }, []);

  return (
    <AppShell>
      <div className="mx-auto w-full max-w-6xl space-y-5 px-4 py-8 md:px-6 lg:py-10">
        <PageHeader
          eyebrow="Research console · measurement"
          title="Measurement workbench"
          description="Constructs, task families, and endpoint definitions for the objective imagery battery. Static definitions remain visible when the local registry is offline."
          meta={
            registry ? (
              <span className="font-mono text-[11px] uppercase tracking-[0.12em] text-signal/70">
                live registry · {Object.keys(registry.endpoints).length} endpoints · {registry.hash.slice(0, 12)}
              </span>
            ) : (
              <span className="font-mono text-[11px] uppercase tracking-[0.12em] text-lock/70">
                {registryError ? "static definitions" : "loading registry"}
              </span>
            )
          }
        />

        <section className="rounded-xl border border-white/10 bg-white/[0.025] p-4">
          <div className="flex flex-wrap items-end justify-between gap-2">
            <div>
              <p className="mono-label text-foreground/45">Construct map</p>
              <h2 className="mt-1 text-xl font-semibold text-foreground">What the battery tries to separate</h2>
            </div>
            <p className="max-w-md text-[11px] leading-5 text-foreground/35">
              Objective endpoints carry the inferential weight. Subjective vividness is secondary and never a primary
              outcome.
            </p>
          </div>
          <div className="mt-3 grid gap-3 md:grid-cols-2">
            {CONSTRUCTS.map((construct) => (
              <article key={construct.domain} className="rounded-lg border border-white/10 bg-black/15 p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span
                    className={`rounded-full border px-2 py-0.5 text-[11px] ${
                      construct.objective
                        ? "border-accent/25 bg-accent/[0.07] text-accent-glow/80"
                        : "border-white/10 bg-white/[0.03] text-foreground/45"
                    }`}
                  >
                    {construct.objective ? "objective" : "subjective"}
                  </span>
                  <h3 className="text-sm font-medium text-foreground/80">{construct.name}</h3>
                </div>
                <p className="mt-1.5 text-xs leading-5 text-foreground/45">{construct.description}</p>
              </article>
            ))}
          </div>
        </section>

        <div className="grid gap-4 lg:grid-cols-[0.85fr_1.15fr]">
          <section className="min-w-0 rounded-xl border border-white/10 bg-white/[0.025] p-4">
            <p className="mono-label text-foreground/45">Task battery</p>
            <h2 className="mt-1 text-lg font-semibold text-foreground">Four task families</h2>
            <ol className="mt-3 space-y-2.5">
              {TASK_BATTERY.map((task, index) => (
                <li key={task.id} className="rounded-lg border border-white/8 bg-black/15 p-3">
                  <div className="flex items-baseline justify-between gap-2">
                    <p className="text-sm font-medium text-foreground/75">{task.family}</p>
                    <span className="font-mono text-[11px] text-foreground/25">{String(index + 1).padStart(2, "0")}</span>
                  </div>
                  <p className="mt-1 text-[11px] leading-5 text-foreground/45">{task.description}</p>
                  <code className="mt-1.5 block font-mono text-[11px] text-foreground/30">{task.id}</code>
                </li>
              ))}
            </ol>
          </section>

          <section className="min-w-0 rounded-xl border border-white/10 bg-white/[0.025] p-4">
            <div className="flex flex-wrap items-end justify-between gap-2">
              <div>
                <p className="mono-label text-foreground/45">Endpoint definitions</p>
                <h2 className="mt-1 text-lg font-semibold text-foreground">Roles and directions</h2>
              </div>
              <span className="font-mono text-[11px] text-foreground/30">{ENDPOINTS.length} endpoints</span>
            </div>
            <div className="mt-3 overflow-x-auto">
              <table className="w-full min-w-[560px] border-collapse text-left text-xs">
                <thead>
                  <tr className="border-b border-white/10 font-mono text-[11px] uppercase tracking-[0.1em] text-foreground/40">
                    <th className="py-2 pr-3 font-normal">Endpoint</th>
                    <th className="py-2 pr-3 font-normal">Role</th>
                    <th className="py-2 pr-3 font-normal">Direction</th>
                    <th className="py-2 font-normal">v</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.07]">
                  {ENDPOINTS.map((endpoint) => (
                    <tr key={endpoint.id}>
                      <td className="py-2.5 pr-3 font-mono text-[11px] text-foreground/65">{endpoint.id}</td>
                      <td className="py-2.5 pr-3">
                        <span className={`inline-flex rounded-full border px-2 py-0.5 text-[11px] ${ROLE_STYLES[endpoint.role] || ROLE_STYLES.key_secondary}`}>
                          {endpoint.role.replaceAll("_", " ")}
                        </span>
                      </td>
                      <td className="py-2.5 pr-3 text-foreground/45">{endpoint.direction.replaceAll("_", " ")}</td>
                      <td className="py-2.5 font-mono text-foreground/40">{endpoint.version}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </div>

        <BoundaryNote>
          These definitions describe a measurement plan. They do not establish that any endpoint is valid, reliable, or
          sensitive to imagery training, and no human-subjects data collection is authorized in this build.
        </BoundaryNote>
      </div>
    </AppShell>
  );
}
