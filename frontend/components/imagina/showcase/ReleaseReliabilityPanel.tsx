"use client";

interface ReleaseInfo { overall_status: string; release_candidate_ready: boolean; checks: string[]; }
interface CiReport { mode: string; passed: boolean; steps: string[]; duration_seconds: number; }
interface ArtifactIndex { n_existing: number; n_missing: number; safe_share_bundle_ready: boolean; }

export function ReleaseReliabilityPanel({ health, ci, artifacts, onRefresh }: {
  health: ReleaseInfo | null; ci: CiReport | null; artifacts: ArtifactIndex | null; onRefresh: () => void;
}) {
  return (
    <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-emerald-500/50">
      <div className="text-foreground/40 uppercase tracking-[0.1em]">Release Reliability (V27)</div>

      {health && (
        <div className="space-y-1">
          <div className="flex justify-between text-[9px]">
            <span className="text-foreground/50">Health</span>
            <span className={health.overall_status === "pass" ? "text-green-400" : "text-amber-400"}>
              {health.overall_status} {health.release_candidate_ready ? "(RC Ready)" : ""}
            </span>
          </div>
        </div>
      )}

      {ci && (
        <div className="flex justify-between text-[9px]">
          <span className="text-foreground/50">CI ({ci.mode})</span>
          <span className={ci.passed ? "text-green-400" : "text-red-400"}>
            {ci.passed ? "Passed" : "Failed"} ({ci.duration_seconds}s)
          </span>
        </div>
      )}

      {artifacts && (
        <div className="flex justify-between text-[9px]">
          <span className="text-foreground/50">Artifacts</span>
          <span className={artifacts.safe_share_bundle_ready ? "text-green-400" : "text-amber-400"}>
            {artifacts.n_existing} existing, {artifacts.n_missing} missing
          </span>
        </div>
      )}

      <div className="text-foreground/50 text-[9px] space-y-1">
        <div>Docker Quickstart:</div>
        <div className="font-mono text-[8px] text-foreground/30">
          docker compose -f docker-compose.release.yml up --build
        </div>
      </div>

      <button onClick={onRefresh} className="px-3 py-1.5 rounded bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 hover:bg-emerald-500/30">
        Refresh
      </button>
    </div>
  );
}
