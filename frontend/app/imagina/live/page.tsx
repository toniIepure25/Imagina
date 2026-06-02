"use client";

import { useState } from "react";
import { useLiveNeuroadaptiveDemo } from "@/hooks/useLiveNeuroadaptiveDemo";

function Badge({ label, color }: { label: string; color: string }) {
  return <span className={`px-2 py-0.5 rounded text-[8px] ${color}`}>{label}</span>;
}

export default function LivePage() {
  const demo = useLiveNeuroadaptiveDemo("demo_user");
  const [checkin, setCheckin] = useState({ vividness: 7, stability: 6, effort: 3, fatigue: 2, confidence: 8, discomfort: 1 });
  const [autoPoll, setAutoPoll] = useState(false);

  const f = demo.latestFrame;
  const active = demo.liveSession?.status === "active";

  return (
    <div className="min-h-screen bg-[#0a0a12] p-6 space-y-4 max-w-4xl mx-auto text-sm">
      <div className="text-center space-y-1 py-4">
        <div className="text-2xl font-bold text-foreground">Live Neuroadaptive Control Room</div>
        <div className="text-foreground/50 text-[10px]">Derived engineering telemetry — not BCI, not neurofeedback validation, not mind-reading</div>
        <div className="text-foreground/30 text-[8px]">Raw EEG included: false</div>
      </div>

      {demo.error && <div className="glass p-2 text-red-400 text-[10px]">{demo.error}</div>}

      <div className="flex flex-wrap gap-2">
        {!active && (
          <button onClick={() => demo.startDemo()} className="px-4 py-2 rounded bg-cyan-500/20 border border-cyan-500/30 text-cyan-300 hover:bg-cyan-500/30">
            Start Live Demo
          </button>
        )}
        {active && (
          <>
            <button onClick={demo.stepDemo} className="px-4 py-2 rounded bg-accent/20 border border-accent/30 text-accent-glow hover:bg-accent/30">Step</button>
            <button onClick={() => demo.submitCheckin(checkin)} className="px-4 py-2 rounded bg-amber-500/20 border border-amber-500/30 text-amber-300 hover:bg-amber-500/30">Submit Check-in</button>
            <button onClick={demo.completeDemo} className="px-4 py-2 rounded bg-green-500/20 border border-green-500/30 text-green-400 hover:bg-green-500/30">Complete</button>
            <button onClick={() => demo.abortDemo()} className="px-4 py-2 rounded bg-red-500/20 border border-red-500/30 text-red-400 hover:bg-red-500/30">Abort</button>
            <button onClick={() => { setAutoPoll(true); demo.setAutoPoll(true); }} className="px-4 py-2 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">Auto-Poll</button>
          </>
        )}
        <button onClick={demo.refresh} className="px-4 py-2 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">Refresh</button>
        <button onClick={async () => { const r = await demo.exportDemo(); alert(JSON.stringify(r, null, 2)); }} className="px-4 py-2 rounded bg-violet-500/20 border border-violet-500/30 text-violet-300 hover:bg-violet-500/30">Export Safe Pack</button>
      </div>

      <div className="grid grid-cols-4 gap-3">
        <div className="glass p-2 text-center text-[10px]">
          <div className="text-foreground/30">Session</div>
          <div className="text-foreground/60">{demo.liveSession ? String((demo.liveSession as Record<string, unknown>).live_session_id || "").slice(0, 12) : "—"}</div>
        </div>
        <div className="glass p-2 text-center text-[10px]">
          <div className="text-foreground/30">Status</div>
          <div className="text-foreground/60">{active ? "Active" : "Idle"}</div>
        </div>
        <div className="glass p-2 text-center text-[10px]">
          <div className="text-foreground/30">Events</div>
          <div className="text-foreground/60">{demo.summary?.n_events ?? 0}</div>
        </div>
        <div className="glass p-2 text-center text-[10px]">
          <div className="text-foreground/30">State</div>
          <div className="text-foreground/60">{String(demo.summary?.latest_adaptive_state || "—").replace(/_/g, " ")}</div>
        </div>
      </div>

      {f && (
        <div className="grid grid-cols-3 gap-3">
          <div className="glass p-3 space-y-2 border-l-2 border-cyan-500/50">
            <div className="text-foreground/40 uppercase text-[9px] tracking-[0.1em]">Signal</div>
            <div className="text-cyan-300 text-lg font-mono">{f.sqi?.toFixed(2)}</div>
            <Badge label={f.gate_state} color={f.gate_state === "open" || f.gate_state === "excellent" ? "bg-green-500/20 text-green-400" : "bg-amber-500/20 text-amber-400"} />
            <div className="text-foreground/20 text-[7px]">Raw EEG: false</div>
          </div>
          <div className="glass p-3 space-y-2 border-l-2 border-emerald-500/50">
            <div className="text-foreground/40 uppercase text-[9px] tracking-[0.1em]">State</div>
            <div className="text-emerald-300 text-lg font-mono">{f.adaptive_state?.replace(/_/g, " ")}</div>
            <Badge label={`conf: ${(f.state_confidence || 0).toFixed(2)}`} color="bg-emerald-500/20 text-emerald-400" />
            <div className="text-foreground/20 text-[7px]">Not neural decoding</div>
          </div>
          <div className="glass p-3 space-y-2 border-l-2 border-amber-500/50">
            <div className="text-foreground/40 uppercase text-[9px] tracking-[0.1em]">Policy</div>
            <div className="text-amber-300 text-lg font-mono">{f.policy_action?.replace(/_/g, " ")}</div>
            <Badge label="preview only" color="bg-amber-500/20 text-amber-400" />
            <div className="text-foreground/20 text-[7px]">No auto-intervention</div>
          </div>
        </div>
      )}

      {active && (
        <div className="glass p-3 space-y-2">
          <div className="text-foreground/40 uppercase text-[9px] tracking-[0.1em]">Check-in</div>
          <div className="grid grid-cols-3 gap-2 text-[9px]">
            {(["vividness", "stability", "effort", "fatigue", "confidence", "discomfort"] as const).map(k => (
              <div key={k}>
                <label className="text-foreground/50">{k} ({checkin[k]})</label>
                <input type="range" min="1" max="10" value={checkin[k]} onChange={e => setCheckin({ ...checkin, [k]: Number(e.target.value) })}
                  className="w-full h-1 bg-surface-border rounded" />
              </div>
            ))}
          </div>
        </div>
      )}

      {demo.events.length > 0 && (
        <div className="glass p-3 space-y-1 border-l-2 border-violet-500/50 max-h-64 overflow-y-auto">
          <div className="text-foreground/40 uppercase text-[9px] tracking-[0.1em]">Event Timeline ({demo.events.length})</div>
          {demo.events.slice(-12).reverse().map((e, i) => (
            <div key={i} className="flex gap-2 text-[8px]">
              <span className="text-foreground/40 w-20 truncate">{(typeof e.event_type === "string" ? e.event_type : "").replace(/_/g, " ")}</span>
              <span className="text-foreground/60 flex-1 truncate">{String(e.payload ?? "").slice(0, 40)}</span>
            </div>
          ))}
        </div>
      )}

      <div className="text-center text-foreground/20 text-[7px] space-y-1">
        <div>Live dashboard events are local engineering telemetry. They are not neural decoding, mental content reconstruction, BCI output, or validated neurofeedback.</div>
      </div>
    </div>
  );
}
