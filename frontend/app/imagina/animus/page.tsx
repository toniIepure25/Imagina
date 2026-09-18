"use client";

import { useCallback, useMemo, useState, type ReactNode } from "react";
import AppShell from "@/components/layout/AppShell";
import {
  ATTRIBUTE_DIRECTIONS,
  OBJECT_CHOICES,
  createSession,
  generateCandidate,
  getTimeline,
  sendFeedback,
  stopSession,
  type AnimusCandidate,
  type AnimusEvent,
  type AnimusState,
} from "@/lib/animusApi";

function Panel({ title, children, hint }: { title: string; children: ReactNode; hint?: string }) {
  return (
    <section className="rounded-xl border border-surface-border bg-surface/30 p-4 space-y-3">
      <div className="flex items-baseline justify-between">
        <h2 className="text-[11px] uppercase tracking-[0.2em] text-accent-glow/70">{title}</h2>
        {hint && <span className="text-[10px] text-foreground/35">{hint}</span>}
      </div>
      {children}
    </section>
  );
}

function ClaimBadge({ label }: { label: string }) {
  return (
    <span className="rounded-full border border-accent-glow/40 bg-accent-glow/10 px-3 py-1 text-[10px] font-mono text-accent-glow">
      {label || "L1 · behavioral-assisted"}
    </span>
  );
}

export default function AnimusWorkspacePage() {
  const [state, setState] = useState<AnimusState | null>(null);
  const [candidates, setCandidates] = useState<AnimusCandidate[]>([]);
  const [events, setEvents] = useState<AnimusEvent[]>([]);
  const [uncertainty, setUncertainty] = useState<number[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const current = candidates.length ? candidates[candidates.length - 1] : null;
  const previous = candidates.length > 1 ? candidates[candidates.length - 2] : null;

  const refreshTimeline = useCallback(async (sid: string) => {
    try {
      const tl = await getTimeline(sid);
      setEvents(tl.events);
      setUncertainty(tl.uncertainty_series);
    } catch (e) {
      setError(String(e));
    }
  }, []);

  const start = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const s = await createSession({ mode: "amplifier", controller: "ANIMUS_ACTIVE" });
      setState(s);
      const g = await generateCandidate(s.session_id, 1, 0);
      setCandidates(g.candidates);
      await refreshTimeline(s.session_id);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }, [refreshTimeline]);

  const applyAndRegenerate = useCallback(
    async (fb: Parameters<typeof sendFeedback>[1]) => {
      if (!state) return;
      setBusy(true);
      setError(null);
      try {
        const s = await sendFeedback(state.session_id, fb);
        setState(s);
        const g = await generateCandidate(s.session_id, 1, 0);
        setCandidates((prev) => [...prev, ...g.candidates]);
        await refreshTimeline(s.session_id);
      } catch (e) {
        setError(String(e));
      } finally {
        setBusy(false);
      }
    },
    [state, refreshTimeline],
  );

  const finish = useCallback(async () => {
    if (!state) return;
    try {
      const s = await stopSession(state.session_id);
      setState(s);
      await refreshTimeline(s.session_id);
    } catch (e) {
      setError(String(e));
    }
  }, [state, refreshTimeline]);

  const uncertaintyTrend = useMemo(() => {
    if (uncertainty.length < 2) return null;
    return uncertainty[uncertainty.length - 1] - uncertainty[0];
  }, [uncertainty]);

  const controllerAction = useMemo(() => {
    const a = [...events].reverse().find((e) => e.event_type === "animus.controller.action");
    const decision = a?.payload?.["decision"] as { action?: string } | undefined;
    return decision?.action ?? "—";
  }, [events]);

  return (
    <AppShell>
      <div className="flex-1 mx-auto w-full max-w-6xl px-5 py-10 space-y-6">
        <header className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-[11px] uppercase tracking-[0.24em] text-accent-glow/70">IMAGINA · ANIMUS</div>
            <h1 className="text-3xl font-bold glow-text">Imagination Amplifier</h1>
            <p className="max-w-2xl text-xs leading-6 text-foreground/55">
              Imagine something, then steer a candidate toward it through a closed human–AI loop. This is a
              behavioral-assisted amplifier — it does not decode neural content.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <ClaimBadge label={state?.claim_label ?? ""} />
            {!state ? (
              <button
                onClick={start}
                disabled={busy}
                className="rounded-lg bg-accent-glow/20 border border-accent-glow/40 px-4 py-2 text-sm text-accent-glow disabled:opacity-40"
              >
                {busy ? "Starting…" : "Start session"}
              </button>
            ) : (
              <button
                onClick={finish}
                className="rounded-lg border border-surface-border px-4 py-2 text-sm text-foreground/70"
              >
                Finish
              </button>
            )}
          </div>
        </header>

        {error && (
          <div className="rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-2 text-xs text-red-300">
            {error} — is the backend running at NEXT_PUBLIC_API_URL?
          </div>
        )}

        <div className="grid gap-5 lg:grid-cols-3">
          <div className="lg:col-span-2 space-y-5">
            <Panel title="Current candidate" hint={current ? `v${candidates.length - 1}` : ""}>
              {current ? (
                <div className="space-y-2">
                  <p className="text-sm text-foreground/80">{current.description}</p>
                  <div className="flex flex-wrap gap-1.5">
                    {current.scene_graph.objects.map((o) => (
                      <span key={o} className="rounded bg-accent-glow/10 px-2 py-0.5 text-[10px] text-accent-glow">
                        {o}
                      </span>
                    ))}
                  </div>
                  <code className="block text-[10px] text-foreground/40">{current.candidate_id}</code>
                </div>
              ) : (
                <p className="text-xs text-foreground/40">Start a session to generate the first candidate.</p>
              )}
            </Panel>

            {previous && (
              <Panel title="Previous version (compare / restore)" hint={`v${candidates.length - 2}`}>
                <div className="flex items-center justify-between gap-3">
                  <p className="text-xs text-foreground/60">{previous.description}</p>
                  <button
                    onClick={() => setCandidates((prev) => [...prev, previous])}
                    className="shrink-0 rounded border border-surface-border px-2 py-1 text-[10px] text-foreground/60"
                  >
                    Restore
                  </button>
                </div>
              </Panel>
            )}

            <Panel title="Feedback — correct & re-imagine">
              <div className="space-y-3">
                <div className="flex flex-wrap gap-1.5">
                  {ATTRIBUTE_DIRECTIONS.map((d) => (
                    <button
                      key={d.direction}
                      disabled={!state || busy}
                      onClick={() => applyAndRegenerate({ channel: "attribute_correction", direction: d.direction })}
                      className="rounded-md border border-surface-border px-2.5 py-1 text-[11px] text-foreground/70 hover:border-accent-glow/40 disabled:opacity-30"
                    >
                      {d.label}
                    </button>
                  ))}
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {OBJECT_CHOICES.map((o) => (
                    <button
                      key={o}
                      disabled={!state || busy}
                      onClick={() => applyAndRegenerate({ channel: "object_correction", object: o, op: "add" })}
                      className="rounded-md border border-surface-border px-2.5 py-1 text-[11px] text-foreground/60 hover:border-accent-glow/40 disabled:opacity-30"
                    >
                      + {o}
                    </button>
                  ))}
                </div>
                <div className="flex gap-2">
                  {current && (
                    <button
                      disabled={busy}
                      onClick={() =>
                        applyAndRegenerate({ channel: "closer_farther", candidate_id: current.candidate_id, closer: true })
                      }
                      className="rounded-md border border-surface-border px-3 py-1 text-[11px] text-foreground/70 disabled:opacity-30"
                    >
                      This is closer
                    </button>
                  )}
                  <button
                    disabled={!state || busy}
                    onClick={() => applyAndRegenerate({ channel: "reimagine" })}
                    className="rounded-md border border-surface-border px-3 py-1 text-[11px] text-foreground/70 disabled:opacity-30"
                  >
                    I am re-imagining it
                  </button>
                </div>
              </div>
            </Panel>

            <Panel title="Iteration timeline">
              <div className="flex flex-wrap items-center gap-1 text-[10px]">
                {candidates.map((c, i) => (
                  <span
                    key={`${c.candidate_id}-${i}`}
                    className={`rounded px-1.5 py-0.5 font-mono ${
                      i === candidates.length - 1 ? "bg-accent-glow/20 text-accent-glow" : "bg-surface/50 text-foreground/40"
                    }`}
                  >
                    v{i}
                  </span>
                ))}
              </div>
            </Panel>
          </div>

          <div className="space-y-5">
            <Panel title="Belief · scene attributes">
              {state ? (
                <ul className="space-y-1 text-[11px]">
                  {Object.entries(state.scene_graph.attributes).map(([k, v]) => (
                    <li key={k} className="flex justify-between">
                      <span className="text-foreground/45">{k}</span>
                      <span className="text-foreground/80">{v}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-foreground/40">—</p>
              )}
            </Panel>

            <Panel title="Uncertainty & amplification">
              <div className="space-y-1 text-[11px]">
                <div className="flex justify-between">
                  <span className="text-foreground/45">global uncertainty</span>
                  <span className="font-mono text-foreground/80">{state?.global_uncertainty?.toFixed(3) ?? "—"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-foreground/45">trend</span>
                  <span className={`font-mono ${uncertaintyTrend != null && uncertaintyTrend < 0 ? "text-emerald-400" : "text-foreground/60"}`}>
                    {uncertaintyTrend != null ? uncertaintyTrend.toFixed(3) : "—"}
                  </span>
                </div>
                <p className="pt-1 text-[10px] text-foreground/40">
                  {uncertaintyTrend != null && uncertaintyTrend < 0
                    ? "Your representation is becoming more stable across this session."
                    : "Keep correcting to stabilize the representation."}
                </p>
              </div>
            </Panel>

            <Panel title="Controller & evidence">
              <div className="space-y-1 text-[11px]">
                <div className="flex justify-between">
                  <span className="text-foreground/45">last action</span>
                  <span className="font-mono text-accent-glow">{controllerAction}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-foreground/45">iteration</span>
                  <span className="font-mono text-foreground/80">{state?.iteration ?? 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-foreground/45">events</span>
                  <span className="font-mono text-foreground/80">{events.length}</span>
                </div>
              </div>
            </Panel>

            <Panel title="Provenance" hint="always visible">
              <p className="text-[10px] leading-5 text-foreground/50">
                Mode: <span className="text-foreground/75">{state?.mode ?? "amplifier"}</span> · Claim:{" "}
                <span className="text-accent-glow">{state?.claim_level ?? "L1_BEHAVIORAL_ASSISTED"}</span>. Observations
                are behavioral/simulated — never decoded thoughts.
              </p>
            </Panel>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
