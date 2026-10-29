"use client";

import { useParams, useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import { useEffect, useRef, useState } from "react";
import AnimusShell from "@/components/animus/AnimusShell";
import Button from "@/components/common/Button";

const AnimusScene = dynamic(() => import("@/components/animus/AnimusScene"), {
  ssr: false,
  loading: () => (
    <div
      role="status"
      aria-label="Loading 3D scene"
      className="flex min-h-[320px] items-center justify-center rounded-xl border border-white/10 bg-[#050711] font-mono text-[11px] uppercase tracking-[0.18em] text-foreground/35"
    >
      Loading scene…
    </div>
  ),
});
import ContrastPair from "@/components/animus/ContrastPair";
import ConfidenceAtlas from "@/components/animus/ConfidenceAtlas";
import ReliabilityPanel from "@/components/animus/ReliabilityPanel";
import EvidenceTrail from "@/components/animus/EvidenceTrail";
import EvidenceMark from "@/components/evidence/EvidenceMark";
import {
  getStudioObservatory,
  getStudioSession,
  getStudioVersion,
  startStudioContrast,
  submitStudioContrast,
  submitStudioContrastReflection,
  type ContrastResult,
  type ContrastSubmit,
  type ContrastThreshold,
  type ContrastTrial,
  type Observatory,
  type SceneGraph,
  type StudioContrast,
  type StudioProfile,
  type StudioSnapshot,
} from "@/lib/animusStudioApi";

type Phase = "idle" | "preview" | "trial" | "complete";

const STRATEGIES = [
  { id: "visual", label: "Visual detail" },
  { id: "spatial", label: "Spatial layout" },
  { id: "verbal", label: "Verbal description" },
  { id: "semantic", label: "Meaning / story" },
  { id: "sensorimotor", label: "Body / movement" },
  { id: "guessing", label: "Mostly guessing" },
];

function newClientTrialId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return `cs_${crypto.randomUUID().replace(/-/g, "").slice(0, 24)}`;
  }
  return `cs_${Date.now().toString(36)}${Math.random().toString(36).slice(2, 10)}`;
}

function number(value: number | null | undefined, digits = 2): string {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(digits) : "—";
}

function thresholdLabel(key: string): string {
  if (key === "spatial_position") return "Spatial position";
  if (key === "object_color") return "Object colour";
  return key.replace(/_/g, " ");
}

function thresholdValue(item: ContrastThreshold): string {
  if (item.threshold === null) return "—";
  if (!item.censored) return item.threshold.toFixed(3);
  return item.threshold <= 0.02 ? "≤ 0.020" : "≥ 0.980";
}

function ResultMetric({
  label,
  value,
  note,
  evidenceId,
}: {
  label: string;
  value: string;
  note: string;
  evidenceId?: string;
}) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
      <div className="flex items-center justify-between gap-2">
        <p className="text-[11px] uppercase tracking-[0.18em] text-foreground/35">{label}</p>
        {evidenceId ? <EvidenceMark evidenceId={evidenceId} /> : null}
      </div>
      <p className="mt-1 text-2xl font-semibold tabular-nums">{value}</p>
      <p className="mt-1 text-[11px] leading-relaxed text-foreground/40">{note}</p>
    </div>
  );
}

export default function AnimusObservatoryPage() {
  const params = useParams<{ sessionId: string }>();
  const router = useRouter();
  const sessionId = params?.sessionId;
  const [session, setSession] = useState<StudioSnapshot | null>(null);
  const [sourceScene, setSourceScene] = useState<SceneGraph | null>(null);
  const [contrast, setContrast] = useState<StudioContrast | null>(null);
  const [trial, setTrial] = useState<ContrastTrial | null>(null);
  const [result, setResult] = useState<ContrastResult | null>(null);
  const [profile, setProfile] = useState<StudioProfile | null>(null);
  const [observatory, setObservatory] = useState<Observatory | null>(null);
  const [phase, setPhase] = useState<Phase>("idle");
  const [selected, setSelected] = useState<"a" | "b" | null>(null);
  const [confidence, setConfidence] = useState(75);
  const [abstained, setAbstained] = useState(false);
  const [strategies, setStrategies] = useState<string[]>([]);
  const [reflectionSaved, setReflectionSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [reflectionBusy, setReflectionBusy] = useState(false);
  const questionStarted = useRef<number>(0);
  const clientTrialId = useRef<string>(newClientTrialId());
  const previewTimer = useRef<number | null>(null);
  const sourceVersionId = useRef<string | null>(null);

  useEffect(() => {
    if (!sessionId) return;
    let active = true;
    void getStudioSession(sessionId)
      .then((loaded) => {
        if (active) {
          setSession(loaded);
          setSourceScene(loaded.scene);
        }
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

  const loadObservatory = async (id: string) => {
    try {
      setObservatory(await getStudioObservatory(id));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    }
  };

  const begin = async () => {
    if (!sessionId || busy || !session) return;
    const repeat = result !== null;
    setBusy(true);
    setError(null);
    setResult(null);
    setObservatory(null);
    setReflectionSaved(false);
    try {
      const started = await startStudioContrast(sessionId, {
        maxTrials: 16,
        formId: "A",
        difficulty: 0.45,
        occasion: repeat ? "follow_up" : "baseline",
        expectedVersionId: session.active_version_id,
      });
      setContrast(started.contrast);
      setTrial(started.trial);
      setProfile(started.profile);
      sourceVersionId.current = started.contrast.source_version_id;
      if (started.contrast.source_version_id !== session.active_version_id) {
        const version = await getStudioVersion(sessionId, started.contrast.source_version_id);
        setSourceScene(version.scene);
      } else {
        setSourceScene(session.scene);
      }
      setPhase("preview");
      if (previewTimer.current !== null) window.clearTimeout(previewTimer.current);
      previewTimer.current = window.setTimeout(() => {
        previewTimer.current = null;
        setPhase("trial");
        resetAnswer();
      }, Math.max(2, started.trial.preview_seconds) * 1000);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setBusy(false);
    }
  };

  const submit = async () => {
    if (!sessionId || !contrast || !trial || busy) return;
    if (!abstained && !selected) return;
    setBusy(true);
    setError(null);
    try {
      const response: ContrastSubmit = await submitStudioContrast(
        sessionId,
        contrast.contrast_id,
        {
          trialId: trial.trial_id,
          taskId: trial.task_id,
          choice: selected ?? undefined,
          confidence: confidence / 100,
          abstained,
          latencyMs: Math.max(0, Date.now() - questionStarted.current),
          clientTrialId: clientTrialId.current,
          expectedVersionId: sourceVersionId.current ?? contrast.source_version_id,
        },
      );
      setProfile(response.profile);
      setContrast(response.contrast);
      if (response.result) {
        setResult(response.result);
        setTrial(null);
        setPhase("complete");
        await loadObservatory(sessionId);
        return;
      }
      if (response.next_trial) {
        setTrial(response.next_trial);
        resetAnswer();
      } else {
        setError("The contrast session returned no next pair and no result. Reload the page.");
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setBusy(false);
    }
  };

  const saveReflection = async () => {
    if (!contrast || reflectionBusy) return;
    setReflectionBusy(true);
    setError(null);
    try {
      const summary = await submitStudioContrastReflection(contrast.contrast_id, {
        strategies,
        notes: "",
      });
      setContrast(summary.contrast);
      setReflectionSaved(true);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setReflectionBusy(false);
    }
  };

  const toggleStrategy = (id: string) => {
    setReflectionSaved(false);
    setStrategies((current) =>
      current.includes(id) ? current.filter((item) => item !== id) : [...current, id],
    );
  };

  const sceneForAtlas = sourceScene ?? session?.scene ?? null;
  const thresholds = result ? Object.entries(result.thresholds) : [];
  const reliability = observatory?.reliability;
  const evidence = observatory?.evidence ?? [];

  return (
    <AnimusShell sessionId={sessionId} active="observatory">
      <div className="mx-auto w-full max-w-6xl px-6 py-10">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <span className="inline-flex rounded-full border border-accent-glow/25 bg-accent-glow/[0.06] px-3 py-1 text-[11px] uppercase tracking-[0.2em] text-accent-glow/75">
              ANIMUS · scene threshold
            </span>
            <h1 className="mt-4 max-w-2xl text-3xl font-semibold tracking-tight md:text-4xl">
              Find the smallest scene change your memory can still detect.
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-relaxed text-foreground/50">
              Two nearly identical scenes. Choose the one that matches what you saw. The next pair adapts
              to your choices. No feedback is shown during the task, so the estimate is not a learning score.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="secondary" onClick={() => router.push(`/animus/studio/${sessionId}`)}>
              Back to Studio
            </Button>
            <Button variant="ghost" onClick={() => router.push("/animus/profile")}>
              Profile
            </Button>
          </div>
        </div>

        {error ? (
          <p className="mt-6 rounded-xl border border-red-400/20 bg-red-400/[0.06] px-4 py-3 text-sm text-red-200/80" role="alert">
            {error}
          </p>
        ) : null}

        {phase === "idle" ? (
          <section className="mt-8 grid gap-5 lg:grid-cols-[1.2fr_0.8fr]">
            <div className="rounded-2xl border border-white/10 bg-white/[0.025] p-6">
              <h2 className="text-lg font-medium">A contrastive memory task</h2>
              <p className="mt-2 text-sm leading-relaxed text-foreground/50">
                You will study one scene, then see 16 pairs. In each pair one scene is unchanged and one
                has a small change. Your choices estimate discrimination sensitivity, a threshold, side
                bias, and confidence calibration — separately.
              </p>
              <ul className="mt-4 space-y-2 text-xs leading-relaxed text-foreground/45">
                <li>· The preview is shown once, from a fixed view.</li>
                <li>· No correctness feedback is shown until the session is complete.</li>
                <li>· Abstaining is recorded as coverage, not as a failure.</li>
                <li>· Thresholds are within-scene and are not imagery-strength scores.</li>
              </ul>
              <div className="mt-6">
                <Button onClick={() => void begin()} disabled={busy || !session}>
                  {busy ? "Preparing…" : "Begin contrast session"}
                </Button>
              </div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/[0.025] p-6">
              <h2 className="text-sm font-medium">What you will see</h2>
              <div className="mt-4 space-y-3 text-xs leading-relaxed text-foreground/50">
                <p><strong className="text-foreground/75">Sensitivity (d′)</strong> — how well you separate the pair overall.</p>
                <p><strong className="text-foreground/75">Threshold</strong> — the change size at about 75% correct.</p>
                <p><strong className="text-foreground/75">Side bias</strong> — whether you favour A or B.</p>
                <p><strong className="text-foreground/75">Calibration</strong> — whether confidence tracks performance.</p>
                <p><strong className="text-foreground/75">Evidence</strong> — which probes support each belief.</p>
                <p><strong className="text-foreground/75">Stability</strong> — whether estimates agree across occasions.</p>
              </div>
              <p className="mt-5 text-[11px] text-foreground/35">
                Experimental behavioural measurement. Not a diagnosis, not neural decoding, and not a
                treatment claim.
              </p>
            </div>
          </section>
        ) : null}

        {phase === "preview" && sceneForAtlas ? (
          <section className="mt-8 overflow-hidden rounded-2xl border border-white/10">
            <AnimusScene
              scene={sceneForAtlas}
              selectedId={null}
              onSelect={() => undefined}
              className="h-[52vh] min-h-[360px]"
              showOverlay={false}
              interactive={false}
            />
            <div className="flex flex-wrap items-center justify-between gap-2 border-t border-white/10 bg-white/[0.02] px-4 py-3">
              <p className="text-sm text-foreground/65">Study the scene. The first pair appears when the preview ends.</p>
              <span className="text-[11px] uppercase tracking-[0.18em] text-foreground/35">
                fixed view · no orbit
              </span>
            </div>
          </section>
        ) : null}

        {phase === "trial" && trial ? (
          <section className="mt-8 space-y-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-[11px] uppercase tracking-[0.2em] text-foreground/35">Trial</p>
                <p className="mt-1 text-lg font-medium tabular-nums">
                  {trial.trial_index + 1} <span className="text-sm font-normal text-foreground/35">of {contrast?.max_trials ?? 16}</span>
                </p>
              </div>
              <div className="h-1.5 w-48 overflow-hidden rounded-full bg-white/10" aria-hidden="true">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-accent-glow/80 to-accent/80"
                  style={{ width: `${Math.min(100, ((trial.trial_index + 1) / (contrast?.max_trials ?? 16)) * 100)}%` }}
                />
              </div>
            </div>

            <ContrastPair trial={trial} selected={selected} onSelect={setSelected} disabled={busy} />

            <div className="rounded-2xl border border-white/10 bg-white/[0.025] p-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <label htmlFor="contrast-confidence" className="text-sm text-foreground/70">
                  Confidence
                </label>
                <span className="text-sm tabular-nums text-foreground/80">{confidence}%</span>
              </div>
              <input
                id="contrast-confidence"
                type="range"
                min={50}
                max={100}
                step={1}
                value={confidence}
                onChange={(event) => setConfidence(Number(event.target.value))}
                className="mt-3 w-full accent-[#7dd3fc]"
              />
              <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
                <label className="flex items-center gap-2 text-xs text-foreground/50">
                  <input
                    type="checkbox"
                    checked={abstained}
                    onChange={(event) => {
                      setAbstained(event.target.checked);
                      if (event.target.checked) setSelected(null);
                    }}
                  />
                  I cannot tell (abstain)
                </label>
                <Button onClick={() => void submit()} disabled={busy || (!abstained && !selected)}>
                  {busy ? "Recording…" : "Record answer"}
                </Button>
              </div>
              <p className="mt-3 text-[11px] text-foreground/35">
                No correctness feedback is shown during the session. The adaptive staircase uses your
                answer server-side.
              </p>
            </div>
          </section>
        ) : null}

        {phase === "complete" && result ? (
          <section className="mt-8 space-y-5">
            <div className="rounded-2xl border border-white/10 bg-white/[0.025] p-6">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-[11px] uppercase tracking-[0.2em] text-accent-glow/70">Session complete</p>
                  <h2 className="mt-1 text-2xl font-semibold">Your discrimination profile</h2>
                  <p className="mt-1 text-xs text-foreground/45">
                    {result.n_answered} answered of {result.n_trials} · {Math.round((result.coverage ?? 0) * 100)}% coverage
                  </p>
                </div>
                <div className="flex gap-2">
                  <Button variant="secondary" onClick={() => void begin()} disabled={busy}>
                    Run another
                  </Button>
                  <Button variant="ghost" onClick={() => void loadObservatory(sessionId ?? "")}>
                    Refresh atlas
                  </Button>
                </div>
              </div>
              <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <ResultMetric label="d′" value={number(result.dprime)} note="overall 2-AFC sensitivity" evidenceId="threshold.dprime" />
                <ResultMetric label="Side bias" value={number(result.side_bias, 3)} note="A share minus 0.5; signed, descriptive" />
                <ResultMetric
                  label="Brier"
                  value={number(result.calibration.brier, 3)}
                  note="lower means confidence tracks performance"
                  evidenceId="calibration.brier"
                />
                <ResultMetric
                  label="Type-2 AUC"
                  value={number(result.calibration.type2_auc, 3)}
                  note="confidence separation; withheld when sparse"
                />
              </div>
              <div className="mt-4 grid grid-cols-2 gap-2 border-t border-white/8 pt-3 sm:grid-cols-4">
                {[
                  ["Trials", String(result.n_trials)],
                  ["Answered", String(result.n_answered)],
                  ["Coverage", `${Math.round((result.coverage ?? 0) * 100)}%`],
                  ["Calibration n", String(result.calibration.n)],
                ].map(([label, value]) => (
                  <div key={label}>
                    <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-foreground/30">{label}</p>
                    <p className="mt-0.5 font-mono text-sm tabular-nums text-foreground/65">{value}</p>
                  </div>
                ))}
              </div>
              {thresholds.some(([, item]) => item.censored) ? (
                <p className="mt-3 text-[11px] leading-relaxed text-lock/65">
                  A censored threshold is shown as an inequality. It records the direction of the evidence, not a
                  precise crossing point.
                </p>
              ) : null}
            </div>

            <div className="rounded-2xl border border-white/10 bg-white/[0.025] p-5">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h2 className="text-sm font-medium">Thresholds</h2>
                <span className="text-[11px] text-foreground/35">75% criterion · within-scene units</span>
              </div>
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                {thresholds.map(([key, item]) => (
                  <div key={key} className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
                    <p className="text-xs text-foreground/60">{thresholdLabel(key)}</p>
                    <p className="mt-1 text-2xl font-semibold tabular-nums">
                      {thresholdValue(item)}
                    </p>
                    <p className="mt-1 text-[11px] text-foreground/40">
                      {item.status === "estimated"
                        ? `${item.n} trials${item.ci ? ` · 95% CI ${item.ci[0].toFixed(2)}–${item.ci[1].toFixed(2)}` : ""}${item.censored ? " · censored" : ""}`
                        : "not enough evidence"}
                    </p>
                  </div>
                ))}
                {thresholds.length === 0 ? (
                  <p className="text-xs text-foreground/40">
                    This scene did not provide enough adaptive feature trials for a threshold.
                  </p>
                ) : null}
              </div>
              <ul className="mt-4 space-y-1 text-[11px] leading-relaxed text-foreground/40">
                {result.notes.map((note) => (
                  <li key={note}>· {note}</li>
                ))}
              </ul>
            </div>

            {observatory && sceneForAtlas ? (
              <ConfidenceAtlas observatory={observatory} scene={sceneForAtlas} />
            ) : (
              <p className="rounded-xl border border-white/10 bg-white/[0.02] px-4 py-3 text-xs text-foreground/40">
                Building the confidence atlas from local evidence…
              </p>
            )}

            <EvidenceTrail items={evidence} />

            {reliability ? <ReliabilityPanel reliability={reliability} /> : null}

            <div className="rounded-2xl border border-white/10 bg-white/[0.025] p-5">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h2 className="text-sm font-medium">How did you do it?</h2>
                <span className="text-[11px] text-foreground/35">optional · descriptive only</span>
              </div>
              <p className="mt-1 text-xs leading-relaxed text-foreground/45">
                Strategy is not a score. It helps interpret the result, especially when visual imagery is
                weak or absent.
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                {STRATEGIES.map((strategy) => {
                  const active = strategies.includes(strategy.id);
                  return (
                    <button
                      key={strategy.id}
                      type="button"
                      aria-pressed={active}
                      onClick={() => toggleStrategy(strategy.id)}
                      className={`rounded-full border px-3 py-1.5 text-xs transition ${
                        active
                          ? "border-accent-glow/60 bg-accent-glow/10 text-foreground"
                          : "border-white/10 text-foreground/50 hover:border-white/20"
                      }`}
                    >
                      {strategy.label}
                    </button>
                  );
                })}
              </div>
              <div className="mt-4 flex items-center gap-3">
                <Button variant="secondary" onClick={() => void saveReflection()} disabled={reflectionBusy}>
                  {reflectionBusy ? "Saving…" : reflectionSaved ? "Saved" : "Save reflection"}
                </Button>
                <span className="text-[11px] text-foreground/35">
                  Stored locally with this contrast session.
                </span>
              </div>
            </div>

            <p className="text-[11px] leading-relaxed text-foreground/35">
              This is a behavioural discrimination estimate, not imagery strength, a diagnosis, or a
              neural reconstruction. A lower threshold means finer discrimination within this scene.
              {profile ? ` Local profile trials: ${profile.trial_count}.` : ""}
            </p>
          </section>
        ) : null}
      </div>
    </AnimusShell>
  );
}

