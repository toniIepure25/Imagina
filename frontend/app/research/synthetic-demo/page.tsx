"use client";

import AppShell from "@/components/layout/AppShell";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface RunStatus {
  run_id: string;
  study_id: string;
  status: string;
  sessions_completed: number;
  sessions_failed: number;
  total_sessions: number;
  export_ready: boolean;
  replay_verified: boolean;
  error: string | null;
}

export default function SyntheticDemoPage() {
  const [studyId, setStudyId] = useState("synthetic-demo-001");
  const [participantCount, setParticipantCount] = useState(6);
  const [seed, setSeed] = useState(42);
  const [runStatus, setRunStatus] = useState<RunStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [polling, setPolling] = useState(false);

  const startStudy = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/synthetic-runtime/studies`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Idempotency-Key": `${studyId}-${Date.now()}`,
        },
        body: JSON.stringify({
          study_id: studyId,
          participant_count: participantCount,
          seed,
          trials_per_session: 5,
          windows_per_trial: 3,
        }),
      });
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error(detail.detail || `HTTP ${res.status}`);
      }
      const data = await res.json();
      setRunStatus({ ...runStatus!, run_id: data.run_id, study_id: studyId, status: "accepted" } as RunStatus);
      setPolling(true);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [studyId, participantCount, seed, runStatus]);

  useEffect(() => {
    if (!polling || !runStatus?.run_id) return;
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/api/synthetic-runtime/runs/${runStatus.run_id}`);
        if (res.ok) {
          const data: RunStatus = await res.json();
          setRunStatus(data);
          if (data.status === "completed" || data.status === "completed_with_failures" || data.status === "failed" || data.status === "aborted") {
            setPolling(false);
          }
        }
      } catch {
        /* polling failure is transient */
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [polling, runStatus?.run_id]);

  return (
    <AppShell>
      <div className="max-w-3xl mx-auto py-8 px-4">
        <h1 className="text-3xl font-bold mb-2">Synthetic Runtime Operator</h1>
        <p className="text-sm text-amber-400 bg-amber-900/20 border border-amber-700/40 rounded-lg px-4 py-2 mb-6">
          Synthetic engineering validation only — not human-subject, behavioral, or neuroscientific evidence.
        </p>

        {!runStatus && (
          <div className="space-y-4 bg-gray-800/50 rounded-xl p-6 border border-gray-700/50">
            <h2 className="text-lg font-semibold">Configure Synthetic Study</h2>
            <div className="grid grid-cols-2 gap-4">
              <label className="space-y-1">
                <span className="text-sm text-gray-400">Study ID</span>
                <input
                  className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm"
                  value={studyId}
                  onChange={(e) => setStudyId(e.target.value)}
                />
              </label>
              <label className="space-y-1">
                <span className="text-sm text-gray-400">Participants</span>
                <input
                  type="number"
                  className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm"
                  value={participantCount}
                  onChange={(e) => setParticipantCount(Number(e.target.value))}
                  min={2}
                  max={60}
                />
              </label>
              <label className="space-y-1">
                <span className="text-sm text-gray-400">Seed</span>
                <input
                  type="number"
                  className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm"
                  value={seed}
                  onChange={(e) => setSeed(Number(e.target.value))}
                />
              </label>
            </div>
            <button
              onClick={startStudy}
              disabled={loading}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 rounded-lg text-sm font-medium"
            >
              {loading ? "Starting..." : "Start Synthetic Study"}
            </button>
            {error && <p className="text-red-400 text-sm">{error}</p>}
          </div>
        )}

        {runStatus && (
          <div className="space-y-4">
            <div className="bg-gray-800/50 rounded-xl p-6 border border-gray-700/50">
              <h2 className="text-lg font-semibold mb-3">Run Progress</h2>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <span className="text-gray-400">Status:</span>{" "}
                  <span className={
                    runStatus.status === "completed" ? "text-emerald-400" :
                    runStatus.status === "failed" ? "text-red-400" :
                    "text-blue-400"
                  }>
                    {runStatus.status}
                  </span>
                </div>
                <div>
                  <span className="text-gray-400">Run ID:</span>{" "}
                  <span className="font-mono text-xs">{runStatus.run_id?.slice(0, 8)}</span>
                </div>
                <div>
                  <span className="text-gray-400">Sessions:</span>{" "}
                  {runStatus.sessions_completed}/{runStatus.total_sessions}
                </div>
                <div>
                  <span className="text-gray-400">Failed:</span>{" "}
                  <span className={runStatus.sessions_failed > 0 ? "text-red-400" : ""}>
                    {runStatus.sessions_failed}
                  </span>
                </div>
                <div>
                  <span className="text-gray-400">Export:</span>{" "}
                  {runStatus.export_ready ? "Ready" : "Pending"}
                </div>
                <div>
                  <span className="text-gray-400">Replay:</span>{" "}
                  {runStatus.replay_verified ? "Verified" : "Pending"}
                </div>
              </div>

              {runStatus.status === "completed" && (
                <div className="mt-4 p-3 bg-emerald-900/20 border border-emerald-700/40 rounded-lg">
                  <p className="text-emerald-400 text-sm font-medium">
                    Synthetic study completed successfully.
                  </p>
                  <p className="text-xs text-gray-400 mt-1">
                    {runStatus.sessions_completed} sessions across 3 conditions (adaptive, fixed, yoked).
                  </p>
                </div>
              )}

              {runStatus.error && (
                <div className="mt-4 p-3 bg-red-900/20 border border-red-700/40 rounded-lg">
                  <p className="text-red-400 text-sm">{runStatus.error}</p>
                </div>
              )}
            </div>

            <button
              onClick={() => { setRunStatus(null); setError(null); }}
              className="text-sm text-gray-400 hover:text-white"
            >
              Start New Study
            </button>
          </div>
        )}

        <div className="mt-8">
          <Link href="/research" className="text-sm text-emerald-400 hover:underline">
            &larr; Back to Research Platform
          </Link>
        </div>
      </div>
    </AppShell>
  );
}
