"use client";

import { useEffect } from "react";
import { useCapstoneDemo } from "@/hooks/useCapstoneDemo";
import { CapstoneReviewerDemoPanel } from "@/components/imagina/live/CapstoneReviewerDemoPanel";
import { CapstoneEvidencePackPanel } from "@/components/imagina/live/CapstoneEvidencePackPanel";
import { CapstoneNarrativePanel } from "@/components/imagina/live/CapstoneNarrativePanel";
import { CapstoneReadinessPanel } from "@/components/imagina/live/CapstoneReadinessPanel";

export function CapstoneDemoPanel({ userId = "demo_user" }: { userId?: string }) {
  const cap = useCapstoneDemo(userId);

  useEffect(() => { cap.refreshAll(); }, [cap.refreshAll]);

  return (
    <div className="space-y-4 text-[10px]">
      {cap.error && <div className="glass p-2 text-red-400 text-[10px]">{cap.error}</div>}

      <div className="text-foreground/40 uppercase tracking-[0.1em]">Capstone Reviewer Demo (V44)</div>
      <div className="text-foreground/30 text-[9px] leading-relaxed">
        One-click unified demo: live demo → scene replay → benchmark → scorecard → Scenario SDK → policy matrix → leaderboard → export.
        <span className="px-1.5 py-0.5 ml-1 rounded bg-cyan-500/20 text-cyan-400 text-[7px]">raw_eeg: false</span>
        <span className="px-1.5 py-0.5 ml-1 rounded bg-green-500/20 text-green-400 text-[7px]">not BCI</span>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-3">
          <CapstoneReviewerDemoPanel
            onRun={() => cap.runDemo()}
            onBuildEvidence={() => cap.buildEvidencePack()}
            onBuildNarrative={() => cap.buildNarrative()}
            onCheckReadiness={() => cap.checkReadiness()}
          />
        </div>
        <div className="space-y-3">
          <CapstoneEvidencePackPanel
            pack={cap.evidencePack as { n_files: number; safe_to_share: boolean; raw_eeg_included: boolean } | null}
            onBuild={() => cap.buildEvidencePack() as Promise<{ n_files: number; safe_to_share: boolean; raw_eeg_included: boolean } | null>}
            onRefresh={() => cap.refreshAll()}
          />
          <CapstoneNarrativePanel
            onBuild={() => cap.buildNarrative()}
            onRefresh={() => cap.refreshAll()}
          />
          <CapstoneReadinessPanel
            readiness={cap.readiness}
            onCheck={() => cap.checkReadiness() as Promise<Record<string, unknown> | null>}
            onRefresh={() => cap.refreshAll()}
          />
        </div>
      </div>
    </div>
  );
}
