"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import AppShell from "@/components/layout/AppShell";
import Button from "@/components/common/Button";
import AnimusScene from "@/components/animus/AnimusScene";
import EpistemicProbe from "@/components/animus/EpistemicProbe";
import {
  getStudioInterview,
  getStudioSession,
  startStudioInterview,
  submitStudioInterview,
  type EpistemicProbe as EpistemicProbeData,
  type EpistemicReconstruction,
  type InterviewSubmit,
  type StudioInterview,
  type StudioProfile,
  type StudioSnapshot,
} from "@/lib/animusStudioApi";

type Phase = "idle" | "preview" | "question" | "complete";

function newClientTrialId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return `ei_${crypto.randomUUID().replace(/-/g, "").slice(0, 24)}`;
  }
  return `ei_${Date.now().toString(36)}${Math.random().toString(36).slice(2, 10)}`;
}

function percent(value: number | null | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "—";
  return `${Math.round(value * 100)}%`;
}

export default function AnimusInterviewPage() {
  const params = useParams<{ sessionId: string }>();
  const router = useRouter();
  const sessionId = params?.sessionId;
  const [session, setSession] = useState<StudioSnapshot | null>(null);
  const [profile, setProfile] = useState<StudioProfile | null>(null);
  const [interview, setInterview] = useState<StudioInterview | null>(null);
  const [probe, setProbe] = useState<EpistemicProbeData | null>(null);
  const [reconstruction, setReconstruction] = useState<EpistemicReconstruction | null>(null);
  const [phase, setPhase] = useState<Phase>("idle");
  const [selected, setSelected] = useState<string | null>(null);
  const [confidence, setConfidence] = useState(75);
  const [abstained, setAbstained] = useState(false);
  const [result, setResult] = useState<InterviewSubmit | null>(null);
  const [sourceVersionId, setSourceVersionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const questionStarted = useRef<number>(0);
  const clientTrialId = useRef<string>(newClientTrialId());
  const previewTimer = useRef<number | null>(null);

  useEffect(() => {
    if (!sessionId) return;
    let active = true;
    void getStudioSession(sessionId)
      .then((loaded) => {
        if (active) setSession(loaded);
      })
      .catch((caught: unknown) => {
        if (active) setError(caught instanceof Error ? caught.message : String(caught));
      });
    return () => {
      active = false;
    };
  }, [sessionId]);

  useEffect(() => () => {
    if (previewTimer.current !== null) window.clearTimeout(previewTimer.current);
  }, []);

  const resetAnswer = () => {
    setSelected(null);
    setAbstained(false);
    setConfidence(75);
    clientTrialId.current = newClientTrialId();
    questionStarted.current = Date.now();
  };

  const begin = async () => {
    if (!sessionId || busy) return;
    setBusy(true);
    setError(null);
    setResult(null);
    setReconstruction(null);
    try {
      const started = await startStudioInterview(sessionId, {
        maxProbes: 12,
        formId: "A",
        difficulty: 0.45,
        expectedVersionId: session?.active_version_id,
      });
      setInterview(started.interview);
      setProbe(started.probe);
      setProfile(started.profile);
      setSourceVersionId(started.interview.source_version_id);
      setPhase("preview");
      if (previewTimer.current !== null) window.clearTimeout(previewTimer.current);
      previewTimer.current = window.setTimeout(() => {
        previewTimer.current = null;
        setPhase("question");
        resetAnswer();
      }, Math.max(2, started.probe.preview_seconds) * 1000);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setBusy(false);
    }
  };

  const submit = async () => {
    if (!sessionId || !interview || !probe || busy) return;
    if (!abstained && !selected) return;
    setBusy(true);
    setError(null);
    try {
      const response = await submitStudioInterview(sessionId, interview.interview_id, {
        probeId: probe.probe_id,
        taskId: probe.task_id,
        choice: abstained ? "" : (selected ?? ""),
        confidence: confidence / 100,
        abstained,
        latencyMs: Math.max(0, Date.now() - questionStarted.current),
        clientTrialId: clientTrialId.current,
        expectedVersionId: sourceVersionId ?? interview.source_version_id,
      });
      setResult(response);
      setProfile(response.profile);
      if (response.interview) setInterview(response.interview);
      if (response.reconstruction) {
        setReconstruction(response.reconstruction);
        setProbe(null);
        setPhase("complete");
        return;
      }
      if (response.next_probe) {
        setProbe(response.next_probe);
        resetAnswer();
        return;
      }
      const summary = await getStudioInterview(interview.interview_id);
      setInterview(summary.interview);
      setReconstruction(summary.reconstruction);
      setProbe(null);
      setPhase("complete");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setBusy(false);
    }
  };

  const restart = () => {
    if (previewTimer.current !== null) {
      window.clearTimeout(previewTimer.current);
      previewTimer.current = null;
    }
    setInterview(null);
    setProbe(null);
    setReconstruction(null);
    setResult(null);
    setPhase("idle");
    void begin();
  };

  const scores = reconstruction?.scores;
  const objectEntropy = reconstruction?.uncertainty.object_entropy;
  const relationEntropy = reconstruction?.uncertainty.relation_entropy;

  return (
    <AppShell>
      <div className="mx-auto w-full max-w-6xl px-6 py-10">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <span className="inline-flex rounded-full border border-accent-glow/25 bg-accent-glow/[0.06] px-3 py-1 text-[10px] uppercase tracking-[0.2em] text-accent-glow/75">
              ANIMUS · epistemic interview
            </span>
            <h1 className="mt-4 text-3xl font-semibold tracking-tight">Ask better questions, not more.</h1>
            <p className="mt-2 max-w-2xl text-sm leading-relaxed text-foreground/50">
              The scene is shown once, then hidden. After two coverage probes, each binary probe is chosen by
              expected information gain, then the belief state is updated from your answer and confidence.
              This is a behavioural reconstruction, not a neural readout.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              onClick={() => router.push(sessionId ? `/animus/studio/${sessionId}` : "/animus")}
            >
              Back to scene
            </Button>
            <Button variant="ghost" onClick={() => router.push("/animus/profile")}>
              View profile
            </Button>
          </div>
        </div>

        {error ? (
          <p className="mt-6 rounded-xl border border-red-400/20 bg-red-400/[0.06] px-4 py-3 text-sm text-red-200/80">
            {error}
          </p>
        ) : null}

        <div className="mt-8 grid gap-6 lg:grid-cols-[1.45fr_0.55fr]">
          <section className="overflow-hidden rounded-2xl border border-white/10 bg-[#070a12]">
            {phase === "idle" ? (
              <div className="flex min-h-[430px] flex-col items-center justify-center p-8 text-center">
                <span className="rounded-full border border-white/10 px-3 py-1 text-[10px] uppercase tracking-[0.18em] text-foreground/40">
                  {session?.title ?? "Loading session"}
                </span>
                <h2 className="mt-4 text-xl font-medium">A short, adaptive interview</h2>
                <p className="mt-2 max-w-md text-sm leading-relaxed text-foreground/45">
                  Twelve probes by default. The first probe covers object presence, then spatial relation,
                  then selection follows expected information gain. You may abstain without penalty.
                </p>
                <Button className="mt-6" onClick={begin} disabled={busy || !session}>
                  {busy ? "Preparing…" : "Start interview"}
                </Button>
              </div>
            ) : phase === "preview" ? (
              <div className="relative">
                {session?.scene ? (
                  <AnimusScene
                    scene={session.scene}
                    selectedId={null}
                    onSelect={() => undefined}
                    showOverlay={false}
                    interactive={false}
                    className="h-[430px] w-full"
                  />
                ) : (
                  <div className="flex min-h-[430px] items-center justify-center p-8 text-sm text-foreground/45">
                    Preparing the scene…
                  </div>
                )}
                <div className="pointer-events-none absolute inset-x-0 bottom-0 z-10 bg-gradient-to-t from-[#050711] via-[#050711]/85 to-transparent px-6 pb-6 pt-16">
                  <p className="text-[10px] uppercase tracking-[0.2em] text-accent-glow/70">Encoding</p>
                  <p className="mt-1 text-lg font-medium">Hold the scene in mind.</p>
                  <p className="mt-1 text-sm text-foreground/45">
                    It hides in {probe?.preview_seconds ?? 4} seconds. The view is fixed. You will not see the
                    scene again during the interview.
                  </p>
                </div>
              </div>
            ) : phase === "question" && probe ? (
              <div className="p-6">
                <div className="mb-4 flex items-center justify-between gap-3 text-[11px] text-foreground/35">
                  <span>
                    Probe {(interview?.probe_count ?? 0) + 1} of {interview?.max_probes ?? 12}
                  </span>
                  <span>Form {interview?.form_id ?? "A"} · {interview?.protocol_version ?? "eri-v1"}</span>
                </div>
                {result?.feedback?.message ? (
                  <p className="mb-4 rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2 text-xs text-foreground/50">
                    {result.feedback.message}
                  </p>
                ) : null}
                <EpistemicProbe
                  probe={probe}
                  selected={selected}
                  confidence={confidence}
                  abstained={abstained}
                  busy={busy}
                  onSelect={setSelected}
                  onConfidence={setConfidence}
                  onAbstain={setAbstained}
                  onSubmit={submit}
                />
              </div>
            ) : phase === "complete" && reconstruction ? (
              <div className="p-6">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-[10px] uppercase tracking-[0.18em] text-emerald-200/65">
                    Interview complete
                  </span>
                  <span className="text-[11px] text-foreground/35">
                    {reconstruction.scores.n_probes} probes · {reconstruction.protocol_version}
                  </span>
                </div>
                <h2 className="mt-2 text-xl font-medium tracking-tight">A reconstruction with uncertainty.</h2>
                <p className="mt-2 max-w-2xl text-sm leading-relaxed text-foreground/50">
                  Each row is a posterior probability from your answers, not a picture of your mind. A
                  probability near 50% means the evidence did not separate presence from absence.
                </p>

                <div className="mt-6 grid gap-4 md:grid-cols-2">
                  <div className="rounded-xl border border-white/10 bg-white/[0.025] p-4">
                    <p className="text-[10px] uppercase tracking-[0.18em] text-foreground/35">
                      Objects · P(present)
                    </p>
                    <ul className="mt-3 space-y-3">
                      {reconstruction.objects.slice(0, 10).map((item, index) => (
                        <li key={`${item.label}-${index}`}>
                          <div className="flex items-center justify-between gap-3 text-xs">
                            <span className="truncate text-foreground/70">{item.label}</span>
                            <span className="tabular-nums text-foreground/50">{percent(item.probability)}</span>
                          </div>
                          <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-white/10">
                            <div
                              className="h-full rounded-full bg-accent-glow/70"
                              style={{ width: `${Math.round(item.probability * 100)}%` }}
                            />
                          </div>
                          <p className="mt-1 text-[10px] text-foreground/30">{item.status.replaceAll("_", " ")}</p>
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div className="rounded-xl border border-white/10 bg-white/[0.025] p-4">
                    <p className="text-[10px] uppercase tracking-[0.18em] text-foreground/35">
                      Spatial relations · P(left)
                    </p>
                    {reconstruction.relations.length ? (
                      <ul className="mt-3 space-y-3">
                        {reconstruction.relations.slice(0, 10).map((item, index) => (
                          <li key={`${item.subject}-${item.object}-${index}`}>
                            <div className="flex items-center justify-between gap-3 text-xs">
                              <span className="truncate text-foreground/70">
                                {item.subject} {item.relation.replaceAll("_", " ")} {item.object}
                              </span>
                              <span className="tabular-nums text-foreground/50">{percent(item.probability)}</span>
                            </div>
                            <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-white/10">
                              <div
                                className="h-full rounded-full bg-emerald-300/60"
                                style={{ width: `${Math.round(item.probability * 100)}%` }}
                              />
                            </div>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="mt-3 text-xs text-foreground/35">
                        No spatial relation was probed in this interview.
                      </p>
                    )}
                  </div>
                </div>

                <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  <Metric label="Object accuracy" value={percent(scores?.object_accuracy)} />
                  <Metric label="Spatial accuracy" value={percent(scores?.spatial_accuracy)} />
                  <Metric label="Coverage" value={percent(scores?.coverage)} />
                  <Metric label="Abstention" value={percent(scores?.abstention_rate)} />
                  <Metric label="Mean Brier (lower is better)" value={typeof scores?.mean_brier === "number" ? scores.mean_brier.toFixed(3) : "—"} />
                  <Metric label="Overconfidence" value={typeof scores?.overconfidence === "number" ? scores.overconfidence.toFixed(3) : "—"} />
                  <Metric label="Object entropy" value={typeof objectEntropy === "number" ? objectEntropy.toFixed(3) : "—"} />
                  <Metric label="Relation entropy" value={typeof relationEntropy === "number" ? relationEntropy.toFixed(3) : "—"} />
                </div>

                <div className="mt-6 flex flex-wrap gap-2">
                  <Button onClick={restart} disabled={busy}>Start another interview</Button>
                  <Button variant="secondary" onClick={() => router.push("/animus/profile")}>
                    See profile
                  </Button>
                </div>
              </div>
            ) : (
              <div className="flex min-h-[430px] items-center justify-center p-8 text-sm text-foreground/45">
                Preparing the next probe…
              </div>
            )}
          </section>

          <aside className="space-y-4">
            <div className="rounded-2xl border border-white/10 bg-white/[0.025] p-5">
              <p className="text-[10px] uppercase tracking-[0.18em] text-foreground/35">Local profile</p>
              <div className="mt-3 flex items-baseline justify-between">
                <span className="text-sm text-foreground/65">Interviews</span>
                <span className="text-2xl font-semibold tabular-nums">{profile?.epistemic?.n_interviews ?? 0}</span>
              </div>
              <div className="mt-2 flex items-baseline justify-between">
                <span className="text-sm text-foreground/65">Probes recorded</span>
                <span className="text-lg font-semibold tabular-nums">{profile?.epistemic?.n_probes ?? 0}</span>
              </div>
              <p className="mt-2 text-[11px] leading-relaxed text-foreground/35">
                The profile is shared across sessions on this machine. The interview never changes the scene.
              </p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/[0.025] p-5">
              <p className="text-[10px] uppercase tracking-[0.18em] text-foreground/35">How selection works</p>
              <p className="mt-2 text-[11px] leading-relaxed text-foreground/45">
                A coverage floor asks one object and one spatial probe first. After that the next probe is the
                one with the highest expected reduction in binary entropy. The model is a mean-field Beta
                posterior; there is no composite imagination score.
              </p>
            </div>
            <div className="rounded-2xl border border-amber-300/15 bg-amber-300/[0.035] p-5">
              <p className="text-[10px] uppercase tracking-[0.18em] text-amber-200/55">Boundary</p>
              <p className="mt-2 text-[11px] leading-relaxed text-foreground/45">
                This is behavioural scene reconstruction, not a diagnosis, treatment, or neural decoder. It
                does not show what you imagined. Stop if you feel fatigued or frustrated. Aphantasia is a
                variation, not a deficit.
              </p>
            </div>
          </aside>
        </div>
      </div>
    </AppShell>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.02] px-3 py-2">
      <p className="text-[10px] uppercase tracking-wide text-foreground/30">{label}</p>
      <p className="mt-1 text-sm tabular-nums text-foreground/75">{value}</p>
    </div>
  );
}
