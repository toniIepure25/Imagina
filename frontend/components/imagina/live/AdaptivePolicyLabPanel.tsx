"use client";

import { useEffect } from "react";
import { useAdaptivePolicyLab } from "@/hooks/useAdaptivePolicyLab";
import { PolicyProfileGalleryPanel } from "@/components/imagina/live/PolicyProfileGalleryPanel";
import { PolicyProfileStudioPanel } from "@/components/imagina/live/PolicyProfileStudioPanel";
import { PolicyProfileRegistryPanel } from "@/components/imagina/live/PolicyProfileRegistryPanel";
import { PolicyBenchmarkMatrixPanel } from "@/components/imagina/live/PolicyBenchmarkMatrixPanel";
import { PolicyLeaderboardPanel } from "@/components/imagina/live/PolicyLeaderboardPanel";
import { PolicyLabExportPanel } from "@/components/imagina/live/PolicyLabExportPanel";

export function AdaptivePolicyLabPanel({ userId = "demo_user" }: { userId?: string }) {
  const lab = useAdaptivePolicyLab(userId);

  useEffect(() => { lab.refreshAll(); }, [lab.refreshAll]);

  return (
    <div className="space-y-4 text-[10px]">
      {lab.error && <div className="glass p-2 text-red-400 text-[10px]">{lab.error}</div>}
      {lab.loading && <div className="glass p-2 text-foreground/50 text-[10px]">Loading...</div>}

      <div className="text-foreground/40 uppercase tracking-[0.1em]">Adaptive Policy Lab (V42)</div>
      <div className="text-foreground/30 text-[9px] leading-relaxed">
        Policy profiles tune symbolic scene/session recommendations only. They do not infer mental content,
        validate neurofeedback, or provide BCI control.
        <span className="px-1.5 py-0.5 ml-1 rounded bg-cyan-500/20 text-cyan-400 text-[7px]">raw_eeg: false</span>
        <span className="px-1.5 py-0.5 ml-1 rounded bg-green-500/20 text-green-400 text-[7px]">not BCI</span>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-3">
          <PolicyProfileGalleryPanel
            policies={lab.builtins}
            onLoadIntoEditor={(p) => lab.setEditorPayload(p as Record<string, unknown>)}
            onRunBenchmark={(pid) => lab.runPolicy(pid)}
          />
          <PolicyProfileStudioPanel
            onValidate={(p) => lab.validateEditorPayload()}
            onImport={(p) => lab.importEditorPayload()}
            onRun={(pid) => lab.runPolicy(pid)}
            onGetExample={() => lab.loadExample()}
          />
          <PolicyProfileRegistryPanel
            policies={lab.profiles}
            onRun={(pid) => lab.runPolicy(pid)}
            onRefresh={() => lab.loadProfiles()}
          />
        </div>
        <div className="space-y-3">
          <PolicyBenchmarkMatrixPanel
            matrix={lab.latestMatrix}
            onRunMatrix={() => lab.runMatrix()}
            onRefresh={() => lab.loadLatestMatrix()}
          />
          <PolicyLeaderboardPanel
            leaderboard={lab.latestLeaderboard}
            onBuild={() => lab.buildLeaderboard()}
            onRefresh={() => lab.loadLeaderboard()}
          />
          <PolicyLabExportPanel onExport={() => lab.exportPolicyLab()} />
        </div>
      </div>
    </div>
  );
}
