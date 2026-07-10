"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import AppShell from "@/components/layout/AppShell";
import { getStudyMode } from "@/lib/research-api";

interface RouteCard {
  href: string;
  title: string;
  description: string;
  status: "available" | "partial" | "planned";
}

const routes: RouteCard[] = [
  {
    href: "/research/operator",
    title: "Operator Dashboard",
    description: "Study management, instrument registry, and system capability status.",
    status: "available",
  },
  {
    href: "/research/participant",
    title: "Participant Workflow",
    description: "Consent flow, imagery self-report task, and session execution.",
    status: "planned",
  },
  {
    href: "/research/eeg-validation",
    title: "EEG Validation Dashboard",
    description: "OpenMIIR dataset analysis, event semantics, StimTracker validation.",
    status: "available",
  },
  {
    href: "/research/synthetic-demo",
    title: "Synthetic End-to-End Demo",
    description: "Deterministic three-condition synthetic study workflow.",
    status: "planned",
  },
];

const statusColors: Record<string, string> = {
  available: "bg-emerald-800/50 text-emerald-300",
  partial: "bg-yellow-800/50 text-yellow-300",
  planned: "bg-gray-700/50 text-gray-400",
};

export default function ResearchLandingPage() {
  const [studyMode, setStudyMode] = useState<string>("loading");

  useEffect(() => {
    getStudyMode()
      .then((data) => setStudyMode(data.study_mode))
      .catch(() => setStudyMode("unavailable"));
  }, []);

  return (
    <AppShell>
      <div className="max-w-4xl mx-auto py-8 px-4">
        <div className="mb-8">
          <h1 className="text-3xl font-bold">Research Platform</h1>
          <p className="text-gray-400 mt-2">
            IMAGINA research tools for study management, experiment governance,
            and EEG validation.
          </p>
          <p className="text-xs text-gray-500 mt-1">
            Application mode: <code className="text-gray-300">{studyMode}</code>
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {routes.map((route) => (
            <Link
              key={route.href}
              href={route.href}
              className="block p-5 bg-white/5 rounded-xl border border-white/10 hover:border-white/20 transition-colors"
            >
              <div className="flex items-start justify-between mb-2">
                <h3 className="font-semibold">{route.title}</h3>
                <span className={`text-xs px-2 py-0.5 rounded ${statusColors[route.status]}`}>
                  {route.status}
                </span>
              </div>
              <p className="text-sm text-gray-400">{route.description}</p>
            </Link>
          ))}
        </div>

        <div className="mt-8 p-4 bg-white/5 rounded-xl border border-white/10 text-xs text-gray-500">
          <p>
            IMAGINA is a research prototype. PID and IQI are experimental proxy metrics.
            All default signals are simulated. This system does not decode thoughts or dreams.
            No human data collection is currently authorized.
          </p>
        </div>
      </div>
    </AppShell>
  );
}
