"use client";

import AppShell from "@/components/layout/AppShell";
import Link from "next/link";

export default function SyntheticDemoPage() {
  return (
    <AppShell>
      <div className="max-w-2xl mx-auto py-8 px-4">
        <h1 className="text-3xl font-bold mb-4">Synthetic End-to-End Demo</h1>

        <div className="p-6 bg-yellow-900/20 rounded-xl border border-yellow-700/40 space-y-3">
          <p className="font-medium text-yellow-300">Merge Gate B Deliverable</p>
          <p className="text-sm text-gray-400">
            The synthetic end-to-end research workflow (study creation, protocol freeze,
            participant enrollment, balanced allocation, three-condition session execution,
            provenance-complete export, and deterministic replay) is planned for Merge Gate B.
          </p>
          <p className="text-sm text-gray-400">
            Current status: governance infrastructure and balanced allocation are implemented.
            Session runtime integration and synthetic orchestration are not yet available.
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
