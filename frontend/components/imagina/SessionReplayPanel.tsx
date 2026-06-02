"use client";

import { useState } from "react";

interface Frame { frame_index: number; phase: string; caption: string; iqi_proxy: number; pid_proxy: number; safety_state: string; scene_parameters: Record<string, number>; }
interface ReplaySummary { clarity_change: number; fog_change: number; stability_change: number; detail_change: number; best_phase: string; hardest_phase: string; }
interface Replay { replay_id: string; n_frames: number; frames: Frame[]; summary: ReplaySummary; visualization_boundary?: string; }

export function SessionReplayPanel({ replay, onBuild, onRefresh }: { replay: Replay | null; onBuild: () => void; onRefresh: () => void }) {
  const [frameIdx, setFrameIdx] = useState(0);

  if (!replay || replay.n_frames < 1) {
    return (
      <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-orange-500/50">
        <div className="text-foreground/40 uppercase tracking-[0.1em]">Session Replay (V22)</div>
        <div className="text-foreground/50">Complete a guided session to build a replay.</div>
        <button onClick={onBuild} className="px-3 py-1.5 rounded bg-orange-500/20 border border-orange-500/30 text-orange-300 hover:bg-orange-500/30">Build Replay</button>
      </div>
    );
  }

  const f = replay.frames[Math.min(frameIdx, replay.frames.length - 1)];
  const sm = replay.summary;

  return (
    <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-orange-500/50">
      <div className="flex justify-between items-center">
        <div className="text-foreground/40 uppercase tracking-[0.1em]">Session Replay (V22)</div>
        <span className="text-foreground/30 text-[8px]">{replay.n_frames} frames</span>
      </div>

      <input type="range" min="0" max={replay.frames.length - 1} value={frameIdx} onChange={e => setFrameIdx(Number(e.target.value))}
        className="w-full h-1 bg-surface-border rounded" />

      {f && (
        <div className="space-y-1 text-[9px]">
          <div className="text-foreground/60">Frame {f.frame_index}: {f.phase}</div>
          <div className="text-foreground/40">IQI: {typeof f.iqi_proxy === "number" ? f.iqi_proxy.toFixed(2) : String(f.iqi_proxy || "—")} | PID: {typeof f.pid_proxy === "number" ? f.pid_proxy.toFixed(2) : String(f.pid_proxy || "—")}</div>
          <div className="grid grid-cols-4 gap-1 text-[7px]">
            {[["Clarity", f.scene_parameters?.clarity], ["Fog", f.scene_parameters?.fog], ["Stab", f.scene_parameters?.stability_anchor], ["Det", f.scene_parameters?.detail_density]].map(([k, v]) => (
              <div key={k} className="p-1 rounded bg-surface/30 text-center"><span className="text-foreground/30">{k}</span><br /><span className="text-foreground/60">{typeof v === "number" ? v.toFixed(2) : String(v || "—")}</span></div>
            ))}
          </div>
        </div>
      )}

      <div className="flex gap-1">
        <button onClick={() => setFrameIdx(Math.max(0, frameIdx - 1))} className="px-2 py-1 rounded bg-surface border border-surface-border text-foreground/50 text-[9px]">◀</button>
        <button onClick={() => setFrameIdx(Math.min(replay.frames.length - 1, frameIdx + 1))} className="px-2 py-1 rounded bg-surface border border-surface-border text-foreground/50 text-[9px]">▶</button>
        <span className="text-foreground/30 text-[8px] ml-2">Best: {sm.best_phase} | Hardest: {sm.hardest_phase}</span>
      </div>

      <div className="text-foreground/30 text-[8px]">Clarity {sm.clarity_change?.toFixed(3)} · Fog {sm.fog_change?.toFixed(3)} · Stab {sm.stability_change?.toFixed(3)}</div>

      <button onClick={onRefresh} className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">Refresh</button>
      <div className="text-foreground/20 text-[7px]">{replay.visualization_boundary}</div>
    </div>
  );
}
