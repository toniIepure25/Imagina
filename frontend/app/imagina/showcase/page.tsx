"use client";

import { useEffect, useState } from "react";

interface Showcase {
  project_title: string; tagline: string; hero_summary: string;
  architecture_modules: string[]; demo_flow: string[];
  latest_protocol: { title: string; completed_blocks: number };
  latest_run: { completion_rate: number };
  benchmark_summary: { avg_iqi_proxy: number; avg_fatigue: number };
  scene_replay_summary: { n_frames: number; clarity_change: number };
  skill_progress_summary: { n_total_sessions: number };
  sdk_summary: { schema_version: string };
  manifest: { protocol_hash: string };
  safe_claims: string[]; forbidden_claims: string[];
  how_to_run: string[]; reviewer_checklist: string[];
  scientific_boundary?: string; visualization_boundary?: string;
}

export default function ShowcasePage() {
  const [s, setS] = useState<Showcase | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("http://localhost:8000/api/imagina/showcase/demo_user")
      .then(r => r.json())
      .then(data => { setS(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-8 text-foreground/50">Loading showcase...</div>;
  if (!s) return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] p-8 space-y-4">
      <div className="text-3xl font-bold text-foreground">IMAGINA</div>
      <div className="text-foreground/50">Local-first mental imagery protocol lab and benchmark SDK</div>
      <div className="text-foreground/30 text-sm max-w-md text-center">Demo data not seeded. Run <code className="bg-surface/50 px-2 py-0.5 rounded">cd backend && python3 -m app.cli.imagina_demo full</code> to bootstrap the showcase.</div>
      <div className="text-foreground/20 text-xs">Then refresh this page.</div>
    </div>
  );

  return (
    <div className="min-h-screen bg-[#0a0a12] p-6 space-y-6 max-w-4xl mx-auto text-sm">
      <div className="text-center space-y-1 py-6">
        <div className="text-3xl font-bold text-foreground">{s.project_title}</div>
        <div className="text-foreground/50">{s.tagline}</div>
        <div className="text-foreground/30 max-w-lg mx-auto text-xs leading-relaxed">{s.hero_summary}</div>
      </div>

      <div className="glass p-4 space-y-2 border-l-2 border-blue-500/50">
        <div className="text-foreground/40 uppercase text-xs tracking-[0.1em]">Architecture</div>
        <div className="flex flex-wrap gap-1">
          {s.architecture_modules?.map((m, i) => (
            <span key={i} className="px-2 py-0.5 rounded bg-blue-500/10 text-blue-300 text-[10px]">{m}</span>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-4 gap-3 text-center text-[10px]">
        {[["Protocol", s.latest_protocol?.title?.slice(0, 20) || "—"], ["Completion", `${(s.latest_run?.completion_rate * 100 || 0).toFixed(0)}%`], ["Avg IQI", s.benchmark_summary?.avg_iqi_proxy?.toFixed(2) || "—"], ["Scene Frames", String(s.scene_replay_summary?.n_frames || "—")]].map(([k, v]) => (
          <div key={k} className="p-2 rounded bg-surface/30">
            <div className="text-foreground/30">{k}</div>
            <div className="text-foreground/60">{v}</div>
          </div>
        ))}
      </div>

      <div className="glass p-4 space-y-2 border-l-2 border-cyan-500/50">
        <div className="text-foreground/40 uppercase text-xs tracking-[0.1em]">Demo Flow</div>
        {s.demo_flow?.map((f, i) => <div key={i} className="text-foreground/50 text-[10px]">{f}</div>)}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="glass p-4 space-y-2 border-l-2 border-green-500/50">
          <div className="text-green-400 uppercase text-xs tracking-[0.1em]">Safe Claims</div>
          {s.safe_claims?.map((c, i) => <div key={i} className="text-foreground/50 text-[10px]">✓ {c}</div>)}
        </div>
        <div className="glass p-4 space-y-2 border-l-2 border-red-500/50">
          <div className="text-red-400 uppercase text-xs tracking-[0.1em]">Forbidden Claims</div>
          {s.forbidden_claims?.map((c, i) => <div key={i} className="text-foreground/40 text-[10px]">✕ {c}</div>)}
        </div>
      </div>

      <div className="glass p-4 space-y-2 border-l-2 border-amber-500/50">
        <div className="text-foreground/40 uppercase text-xs tracking-[0.1em]">How to Run Locally</div>
        {s.how_to_run?.map((c, i) => <div key={i} className="text-foreground/50 text-[10px] font-mono">{c}</div>)}
      </div>

      <div className="glass p-4 space-y-2 border-l-2 border-purple-500/50">
        <div className="text-foreground/40 uppercase text-xs tracking-[0.1em]">Reviewer Checklist</div>
        {s.reviewer_checklist?.map((c, i) => <div key={i} className="text-foreground/50 text-[10px]">{c}</div>)}
      </div>

      <div className="text-center text-foreground/20 text-[8px] space-y-1">
        {s.scientific_boundary && <div>{s.scientific_boundary}</div>}
        {s.visualization_boundary && <div>{s.visualization_boundary}</div>}
      </div>
    </div>
  );
}
