"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import AppShell from "@/components/layout/AppShell";
import PageHeader from "@/components/platform/PageHeader";
import BoundaryNote from "@/components/platform/BoundaryNote";
import { getStudyMode } from "@/lib/research-api";

interface RouteCard {
  href: string;
  title: string;
  description: string;
  status: "available" | "partial" | "planned";
}

const ROUTES: RouteCard[] = [
  {
    href: "/research/design",
    title: "Study Designer",
    description: "Lock and export a falsifiable N-of-1 plan with a hash and explicit boundaries.",
    status: "available",
  },
  {
    href: "/research/participant",
    title: "Participant Mode",
    description: "Local consent, three imagery trials, self-report, timing, and JSON export.",
    status: "available",
  },
  {
    href: "/research/operator",
    title: "Operator dashboard",
    description: "Study management, instrument registry, and system capability status.",
    status: "available",
  },
  {
    href: "/research/eeg-validation",
    title: "EEG validation dashboard",
    description: "OpenMIIR dataset analysis, event semantics, and StimTracker validation.",
    status: "available",
  },
  {
    href: "/research/synthetic-demo",
    title: "Synthetic end-to-end demo",
    description: "Deterministic three-condition synthetic study workflow.",
    status: "available",
  },
  {
    href: "/research/measurement",
    title: "Measurement workbench",
    description: "Construct map, task battery, objective and subjective endpoints, scoring.",
    status: "available",
  },
  {
    href: "/research/design-simulation",
    title: "Design simulation",
    description: "Power, Type-I error, bias, and coverage across a scenario grid.",
    status: "available",
  },
  {
    href: "/research/analysis",
    title: "Analysis workbench",
    description: "Primary estimand, confirmatory model, diagnostics, and sensitivity.",
    status: "available",
  },
];

const STATUS_STYLES: Record<RouteCard["status"], string> = {
  available: "border-signal/25 bg-signal/[0.07] text-signal/85",
  partial: "border-lock/25 bg-lock/[0.07] text-lock/85",
  planned: "border-white/10 bg-white/[0.03] text-foreground/45",
};

const STATUS_LABELS: Record<RouteCard["status"], string> = {
  available: "available",
  partial: "partial",
  planned: "planned",
};

export default function ResearchLandingPage() {
  const [studyMode, setStudyMode] = useState<string>("loading");

  useEffect(() => {
    let active = true;
    getStudyMode()
      .then((data) => {
        if (active) setStudyMode(data.study_mode);
      })
      .catch(() => {
        if (active) setStudyMode("unavailable");
      });
    return () => {
      active = false;
    };
  }, []);

  const available = ROUTES.filter((route) => route.status === "available").length;

  return (
    <AppShell>
      <div className="mx-auto w-full max-w-6xl space-y-5 px-4 py-8 md:px-6 lg:py-10">
        <PageHeader
          eyebrow="Research console"
          title="Study tools and evidence workbench"
          description="A local console for study management, measurement design, EEG validation, and analysis planning. Separate from the participant-facing Studio, and deliberately explicit about what is implemented."
          meta={
            <span className="font-mono text-[11px] uppercase tracking-[0.12em] text-foreground/35">
              application mode · {studyMode}
            </span>
          }
          actions={
            <Link
              href="/science"
              className="inline-flex min-h-10 items-center rounded-lg border border-white/12 px-4 text-sm text-foreground/60 hover:text-foreground"
            >
              Scientific framing
            </Link>
          }
        />

        <div className="grid grid-cols-2 gap-2.5 md:grid-cols-4">
          {[
            ["Tools available", String(available)],
            ["Total surfaces", String(ROUTES.length)],
            ["Study mode", studyMode],
            ["Human data", "not authorized"],
          ].map(([label, value]) => (
            <div key={label} className="rounded-lg border border-white/10 bg-white/[0.025] p-3">
              <p className="font-mono text-[11px] uppercase tracking-[0.1em] text-foreground/40">{label}</p>
              <p className="mt-1.5 truncate text-sm text-foreground/75">{value}</p>
            </div>
          ))}
        </div>

        <section className="grid gap-3 md:grid-cols-2">
          {ROUTES.map((route, index) => (
            <Link
              key={route.href}
              href={route.href}
              className="group relative flex flex-col rounded-xl border border-white/10 bg-white/[0.025] p-4 transition-colors hover:border-accent/30 hover:bg-white/[0.04] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <span className="font-mono text-[11px] text-foreground/25">{String(index + 1).padStart(2, "0")}</span>
                  <h2 className="mt-1 text-base font-semibold text-foreground/85 group-hover:text-foreground">
                    {route.title}
                  </h2>
                </div>
                <span className={`shrink-0 rounded-full border px-2 py-0.5 text-[11px] ${STATUS_STYLES[route.status]}`}>
                  {STATUS_LABELS[route.status]}
                </span>
              </div>
              <p className="mt-2 flex-1 text-sm leading-6 text-foreground/50">{route.description}</p>
              <span className="mt-3 inline-flex items-center gap-1 text-xs text-accent-glow/70 group-hover:text-accent-glow">
                Open
                <span aria-hidden="true">→</span>
              </span>
            </Link>
          ))}
        </section>

        <BoundaryNote>
          IMAGINA is a research prototype. PID and IQI are experimental proxy metrics, all default signals are
          simulated, and no human-subjects data collection is authorized in this build. The console does not decode
          thoughts or dreams.
        </BoundaryNote>
      </div>
    </AppShell>
  );
}
