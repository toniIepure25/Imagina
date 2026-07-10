"use client";

import AppShell from "@/components/layout/AppShell";
import Link from "next/link";

export default function ParticipantPage() {
  return (
    <AppShell>
      <div className="max-w-2xl mx-auto py-8 px-4">
        <h1 className="text-3xl font-bold mb-4">Participant Workflow</h1>

        <div className="p-6 bg-yellow-900/20 rounded-xl border border-yellow-700/40 space-y-3">
          <p className="font-medium text-yellow-300">Not Yet Integrated</p>
          <p className="text-sm text-gray-400">
            The participant-facing consent flow, imagery self-report task, and session
            execution are implemented as isolated components but are not yet wired into
            a live research session. This integration belongs to Merge Gate B.
          </p>
          <p className="text-sm text-gray-400">
            Components available: ConsentGate, ImagerySelfReportTask.
          </p>
        </div>

        <div className="mt-6">
          <Link href="/research" className="text-sm text-emerald-400 hover:underline">
            &larr; Back to Research Platform
          </Link>
        </div>
      </div>
    </AppShell>
  );
}
