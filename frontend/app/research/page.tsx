"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/layout/AppShell";
import OperatorDashboard from "@/components/research/OperatorDashboard";
import { getStudyMode } from "@/lib/research-api";

export default function ResearchPage() {
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
          <h1 className="text-3xl font-bold">Research Protocol Dashboard</h1>
          <p className="text-gray-400 mt-2">
            IMAGINA research tools for study management, participant tracking, and
            experiment governance.
          </p>
        </div>

        {studyMode === "demo" && (
          <div className="mb-6 p-4 bg-yellow-900/30 rounded-xl border border-yellow-700/50 text-sm">
            <p className="font-medium text-yellow-300">Demo Mode Active</p>
            <p className="text-gray-400 mt-1">
              Set <code className="text-yellow-400">IMAGINA_STUDY_MODE=pilot</code> to enable
              study creation and participant management. Demo mode prevents research data collection.
            </p>
          </div>
        )}

        {studyMode === "unavailable" && (
          <div className="mb-6 p-4 bg-red-900/30 rounded-xl border border-red-700/50 text-sm">
            <p className="font-medium text-red-300">Backend Unavailable</p>
            <p className="text-gray-400 mt-1">
              Cannot connect to the IMAGINA backend. Ensure the server is running on port 8000.
            </p>
          </div>
        )}

        <OperatorDashboard />

        <div className="mt-8 p-4 bg-white/5 rounded-xl border border-white/10 text-xs text-gray-500">
          <p>
            IMAGINA is a research prototype. PID and IQI are experimental proxy metrics.
            All default signals are simulated. This system does not decode thoughts or dreams.
          </p>
        </div>
      </div>
    </AppShell>
  );
}
