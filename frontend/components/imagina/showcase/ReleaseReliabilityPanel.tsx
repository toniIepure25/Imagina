"use client";

interface ReleaseInfo { overall_status: string; release_candidate_ready: boolean; checks: string[]; }
interface CiReport { mode: string; passed: boolean; steps: string[]; duration_seconds: number; }
interface ArtifactIndex { n_existing: number; n_missing: number; safe_share_bundle_ready: boolean; }

export function ReleaseReliabilityPanel({ health, ci, artifacts, onRefresh }: {
  health: ReleaseInfo | null; ci: CiReport | null; artifacts: ArtifactIndex | null; onRefresh: () => void;
}) {
  return (
    <div className="glass panel-glow p-4 space-y-3 text-[11px] border-l-2 border-emerald-500/50">
      <div className="text-foreground/40 uppercase tracking-[0.1em]">Release Reliability (V27)</div>

      {health && (
        <div className="space-y-1">
          <div className="flex justify-between text-[11px]">
            <span className="text-foreground/50">Health</span>
            <span className={health.overall_status === "pass" ? "text-signal" : "text-lock"}>
              {health.overall_status} {health.release_candidate_ready ? "(RC Ready)" : ""}
            </span>
          </div>
        </div>
      )}

      {ci && (
        <div className="flex justify-between text-[11px]">
          <span className="text-foreground/50">CI ({ci.mode})</span>
          <span className={ci.passed ? "text-signal" : "text-danger"}>
            {ci.passed ? "Passed" : "Failed"} ({ci.duration_seconds}s)
          </span>
        </div>
      )}

      {artifacts && (
        <div className="flex justify-between text-[11px]">
          <span className="text-foreground/50">Artifacts</span>
          <span className={artifacts.safe_share_bundle_ready ? "text-signal" : "text-lock"}>
            {artifacts.n_existing} existing, {artifacts.n_missing} missing
          </span>
        </div>
      )}

      <div className="text-foreground/50 text-[11px] space-y-1">
        <div>Docker Quickstart:</div>
        <div className="font-mono text-[11px] text-foreground/30">
          docker compose -f docker-compose.release.yml up --build
        </div>
      </div>

      <button onClick={onRefresh} className="px-3 py-1.5 rounded bg-signal/10 border border-signal/25 text-signal hover:bg-signal/20">
        Refresh
      </button>
    </div>
  );
}
