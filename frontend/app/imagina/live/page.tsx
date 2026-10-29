"use client";

import { useState } from "react";
import AppShell from "@/components/layout/AppShell";
import PageHeader from "@/components/platform/PageHeader";
import BoundaryNote from "@/components/platform/BoundaryNote";
import { useLiveNeuroadaptiveDemo } from "@/hooks/useLiveNeuroadaptiveDemo";

function Badge({ label, tone }: { label: string; tone: "ok" | "warn" | "muted" }) {
  const styles = {
    ok: "border-signal/25 bg-signal/10 text-signal/90",
    warn: "border-lock/30 bg-lock/10 text-lock/90",
    muted: "border-white/10 bg-white/[0.03] text-foreground/55",
  };
  return <span className={`inline-flex rounded-full border px-2 py-0.5 font-mono text-[11px] ${styles[tone]}`}>{label}</span>;
}

function downloadJson(value: unknown) {
  const blob = new Blob([JSON.stringify(value, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "imagina-live-safe-pack.json";
  anchor.click();
  URL.revokeObjectURL(url);
}

export default function LivePage() {
  const demo = useLiveNeuroadaptiveDemo("demo_user");
  const [checkin, setCheckin] = useState({ vividness: 7, stability: 6, effort: 3, fatigue: 2, confidence: 8, discomfort: 1 });
  const [autoPoll, setAutoPoll] = useState(false);

  const f = demo.latestFrame;
  const active = demo.liveSession?.status === "active";

  return (
    <AppShell status={active ? "live" : "idle"}>
      <div className="mx-auto w-full max-w-5xl space-y-5 px-4 py-8 md:px-6">
        <PageHeader
          eyebrow="Lab · technical preview"
          title="Live neuroadaptive control room"
          description="Derived engineering telemetry from a local simulated stream. This is not BCI output, validated neurofeedback, mental-content reconstruction, or mind-reading."
          actions={
            <Badge label="Raw EEG: false" tone="muted" />
          }
        />

        {demo.error ? (
          <div role="alert" className="rounded-lg border border-danger/25 bg-danger/[0.05] px-4 py-3 text-sm text-danger/85">
            {demo.error}
          </div>
        ) : null}

        <div className="flex flex-wrap gap-2">
          {!active ? (
            <button
              type="button"
              onClick={() => demo.startDemo()}
              className="inline-flex min-h-11 items-center rounded-lg border border-signal/30 bg-signal/10 px-4 text-sm font-medium text-signal hover:bg-signal/15"
            >
              Start live demo
            </button>
          ) : (
            <>
              <button type="button" onClick={demo.stepDemo} className="inline-flex min-h-11 items-center rounded-lg border border-accent/30 bg-accent/15 px-4 text-sm text-accent-glow hover:bg-accent/25">
                Step
              </button>
              <button type="button" onClick={() => demo.submitCheckin(checkin)} className="inline-flex min-h-11 items-center rounded-lg border border-lock/30 bg-lock/10 px-4 text-sm text-lock hover:bg-lock/15">
                Submit check-in
              </button>
              <button type="button" onClick={demo.completeDemo} className="inline-flex min-h-11 items-center rounded-lg border border-signal/25 bg-signal/10 px-4 text-sm text-signal hover:bg-signal/15">
                Complete
              </button>
              <button type="button" onClick={() => demo.abortDemo()} className="inline-flex min-h-11 items-center rounded-lg border border-danger/30 bg-danger/10 px-4 text-sm text-danger hover:bg-danger/15">
                Abort
              </button>
              <button
                type="button"
                onClick={() => {
                  setAutoPoll(true);
                  demo.setAutoPoll(true);
                }}
                disabled={autoPoll}
                className="inline-flex min-h-11 items-center rounded-lg border border-white/12 px-4 text-sm text-foreground/55 hover:text-foreground disabled:opacity-40"
              >
                {autoPoll ? "Auto-poll on" : "Auto-poll"}
              </button>
            </>
          )}
          <button type="button" onClick={demo.refresh} className="inline-flex min-h-11 items-center rounded-lg border border-white/12 px-4 text-sm text-foreground/55 hover:text-foreground">
            Refresh
          </button>
          <button
            type="button"
            onClick={async () => downloadJson(await demo.exportDemo())}
            className="inline-flex min-h-11 items-center rounded-lg border border-violet-400/25 bg-violet-400/10 px-4 text-sm text-violet-200 hover:bg-violet-400/15"
          >
            Export safe pack
          </button>
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[
            ["Session", demo.liveSession ? String((demo.liveSession as Record<string, unknown>).live_session_id || "").slice(0, 12) : "—"],
            ["Status", active ? "Active" : "Idle"],
            ["Events", String(demo.summary?.n_events ?? 0)],
            ["State", String(demo.summary?.latest_adaptive_state || "—").replace(/_/g, " ")],
          ].map(([label, value]) => (
            <div key={label} className="rounded-lg border border-white/10 bg-white/[0.025] p-3">
              <p className="font-mono text-[11px] uppercase tracking-[0.12em] text-foreground/40">{label}</p>
              <p className="mt-1 truncate text-sm text-foreground/75">{value}</p>
            </div>
          ))}
        </div>

        {f ? (
          <div className="grid gap-3 md:grid-cols-3">
            <div className="rounded-lg border border-signal/20 bg-signal/[0.04] p-3">
              <p className="font-mono text-[11px] uppercase tracking-[0.12em] text-foreground/45">Signal</p>
              <p className="mt-2 font-mono text-2xl text-signal">{f.sqi?.toFixed(2)}</p>
              <div className="mt-2">
                <Badge
                  label={f.gate_state}
                  tone={f.gate_state === "open" || f.gate_state === "excellent" ? "ok" : "warn"}
                />
              </div>
              <p className="mt-2 text-[11px] text-foreground/40">Raw EEG: false</p>
            </div>
            <div className="rounded-lg border border-signal/25 bg-signal/[0.06] p-3">
              <p className="font-mono text-[11px] uppercase tracking-[0.12em] text-foreground/45">State</p>
              <p className="mt-2 font-mono text-2xl text-signal">{f.adaptive_state?.replace(/_/g, " ")}</p>
              <div className="mt-2">
                <Badge label={`conf: ${(f.state_confidence || 0).toFixed(2)}`} tone="ok" />
              </div>
              <p className="mt-2 text-[11px] text-foreground/40">Not neural decoding</p>
            </div>
            <div className="rounded-lg border border-lock/20 bg-lock/[0.04] p-3">
              <p className="font-mono text-[11px] uppercase tracking-[0.12em] text-foreground/45">Policy</p>
              <p className="mt-2 font-mono text-2xl text-lock">{f.policy_action?.replace(/_/g, " ")}</p>
              <div className="mt-2">
                <Badge label="preview only" tone="warn" />
              </div>
              <p className="mt-2 text-[11px] text-foreground/40">No auto-intervention</p>
            </div>
          </div>
        ) : null}

        {active ? (
          <section className="rounded-lg border border-white/10 bg-white/[0.025] p-4">
            <h2 className="mono-label text-foreground/45">Check-in</h2>
            <div className="mt-3 grid gap-3 sm:grid-cols-3">
              {(["vividness", "stability", "effort", "fatigue", "confidence", "discomfort"] as const).map((key) => (
                <div key={key}>
                  <label htmlFor={`live-${key}`} className="text-xs capitalize text-foreground/60">
                    {key} ({checkin[key]})
                  </label>
                  <input
                    id={`live-${key}`}
                    type="range"
                    min="1"
                    max="10"
                    value={checkin[key]}
                    onChange={(event) => setCheckin({ ...checkin, [key]: Number(event.target.value) })}
                    className="mt-1 h-1 w-full cursor-pointer rounded bg-surface-border accent-accent"
                  />
                </div>
              ))}
            </div>
          </section>
        ) : null}

        {demo.events.length > 0 ? (
          <section className="rounded-lg border border-white/10 bg-white/[0.025] p-4">
            <h2 className="mono-label text-foreground/45">Event timeline · {demo.events.length}</h2>
            <div className="mt-2 max-h-64 space-y-1 overflow-y-auto">
              {demo.events.slice(-12).reverse().map((event, index) => (
                <div key={index} className="flex gap-2 border-b border-white/[0.06] py-1.5 text-[11px] last:border-0">
                  <span className="w-24 shrink-0 truncate font-mono text-foreground/40">
                    {(typeof event.event_type === "string" ? event.event_type : "").replace(/_/g, " ")}
                  </span>
                  <span className="flex-1 truncate text-foreground/60">{String(event.payload ?? "").slice(0, 80)}</span>
                </div>
              ))}
            </div>
          </section>
        ) : null}

        <BoundaryNote>
          Live dashboard events are local engineering telemetry. They are not neural decoding, mental-content
          reconstruction, BCI output, or validated neurofeedback.
        </BoundaryNote>
      </div>
    </AppShell>
  );
}
