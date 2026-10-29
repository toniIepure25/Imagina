"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import dynamic from "next/dynamic";
import AppShell from "@/components/layout/AppShell";
import PageHeader from "@/components/platform/PageHeader";
import Button from "@/components/common/Button";
import EvidenceMark from "@/components/evidence/EvidenceMark";
import { DimensionBar, Panel, SourceBadge, Sparkline } from "@/components/multimodal/Widgets";
import { DEFAULT_SCENE_PARAMS, feedbackToScene } from "@/lib/feedbackMapping";
import {
  MODALITIES,
  createSession,
  getCorridor,
  getDecisions,
  getHardwareChecklist,
  getSync,
  listModalities,
  listProtocols,
  runProtocol,
  sendCommand,
  stepSession,
  verifyReplay,
  isSimulated,
  type CorridorAction,
  type Decision,
  type ProviderDescriptor,
  type RealtimeModality,
  type SessionStatus,
  type SyncHealth,
  type Tick,
} from "@/lib/multimodalApi";

const DreamCorridorScene = dynamic(() => import("@/components/scene/DreamCorridorScene"), { ssr: false });

const SERIES: { modality: RealtimeModality; feature: string; title: string; unit: string }[] = [
  { modality: "eeg", feature: "posterior_rel_alpha", title: "EEG posterior relative alpha", unit: "ratio" },
  { modality: "eeg", feature: "theta_beta_ratio", title: "EEG theta/beta", unit: "ratio" },
  { modality: "ecg", feature: "heart_rate", title: "Heart rate", unit: "bpm" },
  { modality: "ecg", feature: "rmssd", title: "HRV RMSSD", unit: "ms" },
  { modality: "eda", feature: "tonic_scl", title: "EDA tonic level", unit: "µS" },
  { modality: "respiration", feature: "resp_rate", title: "Respiration rate", unit: "br/min" },
  { modality: "fnirs", feature: "hbo_recent_mean", title: "fNIRS HbO (long channels)", unit: "µM" },
];

const TABS = ["Live session", "Devices", "Protocols", "Hardware safety"] as const;

export default function MultimodalCommandCenter() {
  const [tab, setTab] = useState<(typeof TABS)[number]>("Live session");
  const [mods, setMods] = useState<RealtimeModality[]>([...MODALITIES]);
  const [mode, setMode] = useState<"shadow" | "feedback_research">("shadow");
  const [policy, setPolicy] = useState<"bounded_rules" | "pid_controller_iqi" | "no_feedback">("bounded_rules");
  const [status, setStatus] = useState<SessionStatus | null>(null);
  const [ticks, setTicks] = useState<Tick[]>([]);
  const [sync, setSync] = useState<SyncHealth | null>(null);
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [corridor, setCorridor] = useState<CorridorAction | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [replay, setReplay] = useState<string | null>(null);
  const busy = useRef(false);
  const sid = status?.session_id ?? "";

  const refresh = useCallback(async (id: string) => {
    const [s, d, c] = await Promise.all([getSync(id), getDecisions(id), getCorridor(id).catch(() => null)]);
    setSync(s.current);
    setDecisions(d.slice().reverse());
    setCorridor(c);
  }, []);

  const start = async () => {
    setError(null);
    setReplay(null);
    setTicks([]);
    try {
      const s = await createSession({ session_id: `cc-${Date.now() % 1e8}`, modalities: mods, duration_s: 240,
        seed: 7, mode, policy, run_to_end: false });
      setStatus(s);
      setRunning(true);
    } catch (e) {
      setError(String(e));
    }
  };

  const step = useCallback(async () => {
    if (!sid || busy.current) return;
    busy.current = true;
    try {
      const r = await stepSession(sid, 1);
      setStatus(r.status);
      setTicks((prev) => [...prev, ...r.ticks].slice(-150));
      await refresh(sid);
      if (r.status.done) setRunning(false);
    } catch (e) {
      setError(String(e));
      setRunning(false);
    } finally {
      busy.current = false;
    }
  }, [sid, refresh]);

  useEffect(() => {
    if (!running) return;
    const h = setInterval(step, 400);
    return () => clearInterval(h);
  }, [running, step]);

  const command = async (action: "pause" | "resume" | "emergency_stop") => {
    if (!sid) return;
    const s = await sendCommand(sid, action);
    setStatus(s);
    if (action === "emergency_stop") setRunning(false);
    else await step();
  };

  const last = ticks[ticks.length - 1];
  const simulated = status ? isSimulated(status.source_kinds) : true;
  const scene = useMemo(() => (corridor ? feedbackToScene(corridor.scene) : DEFAULT_SCENE_PARAMS), [corridor]);

  return (
    <AppShell status={status ? status.controller_state : undefined}>
      <div className="w-full max-w-7xl mx-auto px-4 py-6 space-y-4 md:px-6">
        <PageHeader
          eyebrow="Multimodal research"
          title="Acquisition command center"
          description="Synchronized synthetic streams feed proxy estimates and safety-gated feedback. Every decision records its evidence class; nothing here decodes thoughts or imagery."
          actions={
            <div role="tablist" aria-label="Multimodal sections" className="flex flex-wrap gap-1">
              {TABS.map((t) => (
                <button
                  key={t}
                  type="button"
                  role="tab"
                  aria-selected={tab === t}
                  onClick={() => setTab(t)}
                  className={`min-h-9 rounded-lg px-3 text-xs ${
                    tab === t
                      ? "bg-accent text-white"
                      : "border border-white/10 text-foreground/55 hover:bg-white/[0.04] hover:text-foreground"
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>
          }
        />

        <div className="rounded-lg border border-warning/40 bg-warning/5 px-4 py-2.5 text-xs leading-5 text-foreground/70">
          {simulated
            ? "SYNTHETIC / REPLAY data. Waveforms come from deterministic generators or recorded files; they are not measurements of a person, and participant ratings come from a scripted synthetic responder."
            : "REAL SENSOR stream present. Participant-facing feedback stays disabled (ACTIVE_SHADOW) unless a complete authorization is on file."}{" "}
          IMAGINA does not decode thoughts or imagery; estimates below are proxies with stated evidence classes.
        </div>

        {tab === "Live session" && (
          <>
            <Panel title="Session control" hint="Shadow mode computes decisions without delivering them">
              <div className="flex flex-wrap items-end gap-4 text-xs">
                <fieldset className="space-y-1">
                  <legend className="text-foreground/50 mb-1">Modalities</legend>
                  <div className="flex flex-wrap gap-2">
                    {MODALITIES.map((m) => (
                      <label key={m} className="flex items-center gap-1">
                        <input type="checkbox" checked={mods.includes(m)} disabled={running}
                          onChange={() => setMods((p) => (p.includes(m) ? p.filter((x) => x !== m) : [...p, m]))} />
                        {m}
                      </label>
                    ))}
                  </div>
                </fieldset>
                <label className="space-y-1">
                  <div className="text-foreground/50">Mode</div>
                  <select value={mode} disabled={running} onChange={(e) => setMode(e.target.value as typeof mode)}
                    className="bg-background border border-surface-border rounded px-2 py-1">
                    <option value="shadow">ACTIVE_SHADOW (default)</option>
                    <option value="feedback_research">FEEDBACK_RESEARCH (simulation only)</option>
                  </select>
                </label>
                <label className="space-y-1">
                  <div className="text-foreground/50">Policy</div>
                  <select value={policy} disabled={running} onChange={(e) => setPolicy(e.target.value as typeof policy)}
                    className="bg-background border border-surface-border rounded px-2 py-1">
                    <option value="bounded_rules">Bounded rules</option>
                    <option value="pid_controller_iqi">PID controller (IQI setpoint)</option>
                    <option value="no_feedback">No feedback</option>
                  </select>
                </label>
                <div className="flex flex-wrap gap-2">
                  <Button size="sm" onClick={start} disabled={running || mods.length === 0}>Start simulation</Button>
                  <Button size="sm" variant="secondary" onClick={() => setRunning((r) => !r)} disabled={!status || status.done}>
                    {running ? "Hold stepping" : "Continue stepping"}
                  </Button>
                  <Button size="sm" variant="secondary" onClick={() => command("pause")} disabled={!status || status.done}>Pause</Button>
                  <Button size="sm" variant="secondary" onClick={() => command("resume")}
                    disabled={!status || status.controller_state !== "PAUSED"}>Resume (shadow)</Button>
                  <Button size="sm" variant="secondary" disabled={!status || ticks.length === 0}
                    onClick={async () => {
                      const r = await verifyReplay(sid);
                      setReplay(r.reproduced ? `Replay reproduced ${r.n} decisions (hash ${r.final_hash.slice(0, 12)})` : "Replay mismatch");
                    }}>Verify replay</Button>
                </div>
                <Button variant="danger" onClick={() => command("emergency_stop")} disabled={!status || status.done}
                  className="ml-auto font-bold tracking-wide">EMERGENCY STOP</Button>
              </div>
              {status && (
                <div className="flex flex-wrap items-center gap-3 text-xs text-foreground/60">
                  {status.source_kinds.map((k) => <SourceBadge key={k} kind={k} />)}
                  <span>t = {status.t.toFixed(0)} / {status.duration_s}s</span>
                  <span className="font-mono">state: {status.controller_state}</span>
                  <span>policy: {status.policy}</span>
                  {replay && <span className="text-success">{replay}</span>}
                </div>
              )}
              {error && <div className="text-xs text-danger">{error}</div>}
            </Panel>

            <div className="grid gap-4 lg:grid-cols-3">
              <Panel title="Live signal features" hint="Derived from synchronized windows">
                <div className="space-y-3">
                  {SERIES.filter((s) => mods.includes(s.modality)).map((s) => (
                    <Sparkline key={`${s.modality}.${s.feature}`} title={s.title} unit={s.unit}
                      points={ticks.map((tk) => ({ t: tk.t, v: tk.features[s.modality]?.[s.feature] ?? null }))} />
                  ))}
                </div>
              </Panel>

              <Panel title="Imagery state estimates" hint="Each value states its evidence class">
                {last ? (
                  <div className="space-y-3">
                    {Object.entries(last.dimensions).map(([k, d]) => (
                      <DimensionBar key={k} name={k} value={d.value} uncertainty={d.uncertainty} evidence={d.evidence} />
                    ))}
                    <div className="flex flex-wrap items-center gap-2 border-t border-surface-border pt-2 text-[11px] text-foreground/50">
                      <span className="inline-flex items-center gap-1.5">
                        IQI (experimental proxy): {last.iqi === null ? "—" : last.iqi.toFixed(2)}
                        <EvidenceMark evidenceId="iqi.proxy" />
                      </span>
                      <span>overall confidence {last.confidence.toFixed(2)}</span>
                      <span className="inline-flex items-center gap-1.5">
                        PID research metric (not a control target):{" "}
                        {last.pid_research_metric === null ? "—" : last.pid_research_metric.toFixed(2)}
                        <EvidenceMark evidenceId="pid.proxy" />
                      </span>
                    </div>
                  </div>
                ) : <p className="text-xs text-foreground/40">Start a simulation to see estimates.</p>}
              </Panel>

              <Panel title="Dream Corridor" hint={corridor?.delivered ? "feedback delivered" : "neutral scene (not delivered)"}>
                <div className="h-56 rounded-lg overflow-hidden border border-surface-border">
                  <DreamCorridorScene params={scene} />
                </div>
                {corridor && (
                  <div className="text-xs space-y-1">
                    <p className="text-foreground/80 italic">“{corridor.scene.prompt_text}”</p>
                    <p className="text-foreground/50">audio guidance {corridor.audio.guidance_level.toFixed(2)} · ambient{" "}
                      {corridor.audio.ambient_level.toFixed(2)} · script {corridor.audio.script_id} · {corridor.policy_version}</p>
                  </div>
                )}
              </Panel>
            </div>

            <div className="grid gap-4 lg:grid-cols-2">
              <Panel title="Synchronization health" hint={sync?.alignment_note}>
                {sync ? (
                  <table className="w-full text-[11px]">
                    <thead className="text-foreground/50 text-left">
                      <tr><th>stream</th><th>method</th><th>drift ppm</th><th>jitter ms</th><th>align ± ms</th><th>age s</th><th>warnings</th></tr>
                    </thead>
                    <tbody className="font-mono">
                      {Object.entries(sync.streams).map(([id, s]) => (
                        <tr key={id} className="border-t border-surface-border">
                          <td className="py-1">{s.modality} {s.connected ? "" : "⚠ disconnected"}</td>
                          <td>{s.sync_method}</td>
                          <td>{s.clock_drift_ppm.toFixed(1)}</td>
                          <td>{s.jitter_sd_ms.toFixed(2)}</td>
                          <td>{s.alignment_uncertainty_ms === null ? "unknown" : s.alignment_uncertainty_ms.toFixed(2)}</td>
                          <td>{s.data_age_s === null ? "—" : s.data_age_s.toFixed(2)}</td>
                          <td className="text-warning/90">{s.warnings.join(", ")}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : <p className="text-xs text-foreground/40">No streams.</p>}
              </Panel>

              <Panel title="Neurofeedback policy monitor" hint="Hash-chained decision trace">
                <div className="space-y-1 text-[11px] font-mono max-h-72 overflow-y-auto">
                  {decisions.map((d) => (
                    <div key={d.tick} className="flex flex-wrap gap-2 border-b border-surface-border py-1">
                      <span className="text-foreground/40">t={d.t.toFixed(0)}</span>
                      <span>{d.controller_state}</span>
                      <span className={d.delivered ? "text-success" : "text-foreground/40"}>{d.delivered ? "delivered" : "not delivered"}</span>
                      {d.hold_reason && <span className="text-warning">hold: {d.hold_reason}</span>}
                      {d.adaptation_note && <span className="text-foreground/50">{d.adaptation_note}</span>}
                      {d.safety_findings.filter((f) => f.severity !== "hold").map((f) => (
                        <span key={f.code} className="text-danger">⚠ {f.code}</span>
                      ))}
                      <span className="text-foreground/30 ml-auto">{d.hash.slice(0, 10)}</span>
                    </div>
                  ))}
                  {decisions.length === 0 && <p className="text-foreground/40">No decisions yet.</p>}
                </div>
              </Panel>
            </div>
          </>
        )}

        {tab === "Devices" && <DevicesTab />}
        {tab === "Protocols" && <ProtocolsTab />}
        {tab === "Hardware safety" && <HardwareTab />}
      </div>
    </AppShell>
  );
}

function DevicesTab() {
  const [providers, setProviders] = useState<ProviderDescriptor[]>([]);
  useEffect(() => { listModalities().then((r) => setProviders(r.providers)).catch(() => setProviders([])); }, []);
  return (
    <Panel title="Device & modality registry" hint="Support level is reported, not assumed">
      <table className="w-full text-xs">
        <thead className="text-left text-foreground/50">
          <tr><th>provider</th><th>modality</th><th>source</th><th>support</th><th>realtime</th><th>available</th><th>note</th></tr>
        </thead>
        <tbody>
          {providers.map((p) => (
            <tr key={p.provider_id} className="border-t border-surface-border">
              <td className="py-1 font-mono">{p.provider_id}</td>
              <td>{p.modality}</td>
              <td><SourceBadge kind={p.source_kind} /></td>
              <td className="font-mono text-[11px]">{p.support_level}</td>
              <td>{p.realtime ? "yes" : "offline"}</td>
              <td>{p.available ? "yes" : `no${p.requires_package ? ` (needs ${p.requires_package})` : ""}`}</td>
              <td className="text-foreground/50">{p.note}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Panel>
  );
}

function ProtocolsTab() {
  const [specs, setSpecs] = useState<Record<string, Record<string, unknown>>>({});
  const [results, setResults] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<string | null>(null);
  useEffect(() => { listProtocols().then(setSpecs).catch(() => setSpecs({})); }, []);
  return (
    <Panel title="Experimental protocols A–G" hint="Runs on synthetic data; E–G are design simulations">
      <div className="grid gap-3 md:grid-cols-2">
        {Object.entries(specs).map(([id, s]) => (
          <div key={id} className="rounded-lg border border-surface-border p-3 space-y-2 text-xs">
            <div className="flex items-center justify-between">
              <strong>{id}. {String(s.name)}</strong>
              <Button size="sm" variant="secondary" disabled={busy !== null}
                onClick={async () => {
                  setBusy(id);
                  try {
                    const r = await runProtocol(id);
                    setResults((p) => ({ ...p, [id]: `${r.scope}\n${JSON.stringify(r.result, null, 1).slice(0, 900)}` }));
                  } finally { setBusy(null); }
                }}>{busy === id ? "Running…" : "Run (synthetic)"}</Button>
            </div>
            <p className="text-foreground/60">Primary: {String(s.primary)}</p>
            {results[id] && <pre className="whitespace-pre-wrap text-[11px] text-foreground/60 max-h-48 overflow-y-auto">{results[id]}</pre>}
          </div>
        ))}
      </div>
    </Panel>
  );
}

function HardwareTab() {
  const [chk, setChk] = useState<Awaited<ReturnType<typeof getHardwareChecklist>> | null>(null);
  useEffect(() => { getHardwareChecklist().then(setChk).catch(() => setChk(null)); }, []);
  if (!chk) return <Panel title="Hardware validation"><p className="text-xs text-foreground/40">Checklist unavailable.</p></Panel>;
  return (
    <Panel title="Hardware validation checklist" hint={chk.status}>
      <p className="text-xs text-foreground/60">{chk.scope}</p>
      {chk.sections.map((s) => (
        <div key={s.name} className="space-y-1">
          <h3 className="text-xs font-semibold text-foreground/80">{s.name}</h3>
          <ul className="text-xs text-foreground/60 space-y-0.5">
            {s.items.map((i) => (
              <li key={i.id}><span className="font-mono text-foreground/40">{i.id}</span> {i.check}
                {i.gating && <span className="ml-1 text-warning">(gating)</span>}</li>
            ))}
          </ul>
        </div>
      ))}
    </Panel>
  );
}
