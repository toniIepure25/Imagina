"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import AppShell from "@/components/layout/AppShell";
import AsyncState from "@/components/platform/AsyncState";
import BoundaryNote from "@/components/platform/BoundaryNote";
import PageHeader from "@/components/platform/PageHeader";
import Panel from "@/components/platform/Panel";
import OperatorDashboard from "@/components/research/OperatorDashboard";
import { getStudyMode } from "@/lib/research-api";

export default function OperatorPage() {
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

  return (
    <AppShell>
      <div className="mx-auto w-full max-w-5xl space-y-5 px-4 py-8 md:px-6 lg:py-10">
        <PageHeader
          eyebrow="Research operations"
          title="Operator dashboard"
          description="Study management, instrument registry, and system capability status. Human collection stays default-denied in this build."
          meta={
            <span className="inline-flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.12em] text-foreground/35">
              application mode · {studyMode}
            </span>
          }
          actions={
            <Link
              href="/method"
              className="inline-flex h-11 items-center rounded-lg border border-surface-border px-3 text-[11px] text-foreground/60 hover:bg-white/[0.04] hover:text-foreground"
            >
              Method &amp; claims
            </Link>
          }
        />

        {studyMode === "loading" ? (
          <AsyncState kind="loading" title="Reading local study mode" body="Checking the local backend configuration." />
        ) : null}

        {studyMode === "demo" ? (
          <Panel className="border-lock/30 bg-lock/[0.045] p-4">
            <p className="text-sm font-medium text-lock">Demo mode active</p>
            <p className="mt-1 text-sm leading-6 text-foreground/55">
              Set <code className="font-mono text-[11px] text-lock">IMAGINA_STUDY_MODE=pilot</code> to enable study
              creation and participant management. Demo mode prevents research data collection.
            </p>
          </Panel>
        ) : null}

        {studyMode === "unavailable" ? (
          <Panel className="border-danger/30 bg-danger/[0.045] p-4">
            <p className="text-sm font-medium text-danger">Backend unavailable</p>
            <p className="mt-1 text-sm leading-6 text-foreground/55">
              Cannot connect to the local IMAGINA backend. Start it on port 8000, then reload this page.
            </p>
          </Panel>
        ) : null}

        {studyMode !== "loading" ? <OperatorDashboard /> : null}

        <BoundaryNote>
          IMAGINA is a research prototype. PID and IQI are experimental proxy metrics, default signals are simulated,
          and this system does not decode thoughts or dreams. Capability flags describe the local build, not a
          scientific validation.
        </BoundaryNote>
      </div>
    </AppShell>
  );
}
