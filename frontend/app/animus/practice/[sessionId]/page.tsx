"use client";

import { useParams, useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import { useEffect, useMemo, useRef, useState } from "react";
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
import ReconstructionBoard from "@/components/animus/ReconstructionBoard";
import SceneSketch from "@/components/animus/SceneSketch";
import {
  getStudioSession,
  startStudioPractice,
  submitStudioPractice,
  type PracticeAdaptive,
  type PracticePlacement,
  type PracticeResponse,
  type PracticeSubmit,
  type PracticeTask,
  type StudioProfile,
  type StudioSnapshot,
} from "@/lib/animusStudioApi";

type Phase = "idle" | "preview" | "question" | "feedback";

function newClientTrialId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return `tr_${crypto.randomUUID().replace(/-/g, "").slice(0, 24)}`;
  }
  return `tr_${Date.now().toString(36)}${Math.random().toString(36).slice(2, 10)}`;
}

function dimensionLabel(profile: StudioProfile | null, id: string): string {
  return profile?.dimensions.find((dimension) => dimension.id === id)?.label ?? id;
}

export default function AnimusPracticePage() {
  const params = useParams<{ sessionId: string }>();
  const router = useRouter();
  const sessionId = params?.sessionId;
  const [session, setSession] = useState<StudioSnapshot | null>(null);
  const [task, setTask] = useState<PracticeTask | null>(null);
  const [profile, setProfile] = useState<StudioProfile | null>(null);
  const [sourceVersionId, setSourceVersionId] = useState<string | null>(null);
  const [phase, setPhase] = useState<Phase>("idle");
  const [selected, setSelected] = useState<string | null>(null);
  const [selectedTokens, setSelectedTokens] = useState<string[]>([]);
  const [placements, setPlacements] = useState<PracticePlacement[]>([]);
  const [confidence, setConfidence] = useState(55);
  const [result, setResult] = useState<PracticeSubmit | null>(null);
  const [nextTask, setNextTask] = useState<PracticeTask | null>(null);
  const [adaptive, setAdaptive] = useState<PracticeAdaptive | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const questionStarted = useRef<number>(0);

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

  useEffect(() => {
    if (phase !== "preview" || !task) return;
    const timer = window.setTimeout(() => {
      setPhase("question");
      questionStarted.current = Date.now();
    }, Math.max(2, task.preview_seconds) * 1000);
    return () => window.clearTimeout(timer);
  }, [phase, task]);

  const revealQuestion = () => {
    setPhase("question");
    questionStarted.current = Date.now();
  };

  const resetAnswer = () => {
    setSelected(null);
    setSelectedTokens([]);
    setPlacements([]);
  };

  const begin = async () => {
    if (!sessionId || busy) return;
    setBusy(true);
    setError(null);
    resetAnswer();
    setConfidence(55);
    setResult(null);
    setNextTask(null);
    try {
      const started = await startStudioPractice(sessionId);
      setTask(started.task);
      setProfile(started.profile);
      setSourceVersionId(started.source_version_id);
      setAdaptive(started.adaptive);
      setPhase("preview");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setBusy(false);
    }
  };

  const canSubmit = (() => {
    if (!task) return false;
    if (task.response_kind === "token_selection") return selectedTokens.length > 0;
    if (task.response_kind === "spatial_placement") {
      return task.tokens.length > 0 && placements.length === task.tokens.length;
    }
    return Boolean(selected);
  })();

  const submit = async () => {
    if (!sessionId || !task || !canSubmit || busy) return;
    const answer: PracticeResponse = task.response_kind === "token_selection"
      ? { selected_token_ids: selectedTokens }
      : task.response_kind === "spatial_placement"
        ? { placements }
        : { option_id: selected ?? "" };
    setBusy(true);
    setError(null);
    try {
      const response = await submitStudioPractice(sessionId, {
        taskId: task.task_id,
        taskType: task.task_type,
        taskSeed: task.task_seed,
        difficulty: task.difficulty,
        response: answer,
        confidence: confidence / 100,
        latencyMs: Math.max(0, Date.now() - questionStarted.current),
        clientTrialId: newClientTrialId(),
        expectedVersionId: sourceVersionId ?? undefined,
      });
      setResult(response);
      setProfile(response.profile);
      setNextTask(response.next_task ?? null);
      setAdaptive(response.adaptive ?? null);
      setPhase("feedback");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setBusy(false);
    }
  };

  const advance = () => {
    if (!nextTask) {
      void begin();
      return;
    }
    setTask(nextTask);
    setNextTask(null);
    setResult(null);
    resetAnswer();
    setConfidence(55);
    setPhase("preview");
  };

  const candidateOptions = useMemo(
    () => (task?.task_type === "candidate_discrimination"
      ? task.options.filter((option) => option.scene)
      : []),
    [task],
  );
  const correctLabel = result?.feedback?.correct_option_label;
  const errorProfile: Record<string, unknown> = result?.feedback?.error_profile ?? {};
  const omissions = Number(errorProfile.omissions ?? 0);
  const intrusions = Number(errorProfile.intrusions ?? 0);
  const meanSpatialError = typeof errorProfile.mean_spatial_error === "number"
    ? errorProfile.mean_spatial_error.toFixed(2)
    : null;
  const toggleToken = (tokenId: string) => {
    setSelectedTokens((current) => current.includes(tokenId)
      ? current.filter((item) => item !== tokenId)
      : [...current, tokenId]);
  };

  const placeToken = (tokenId: string, x: number, z: number) => {
    setPlacements((current) => [
      ...current.filter((item) => item.token_id !== tokenId),
      { token_id: tokenId, x, z },
    ]);
  };

  return (
    <AnimusShell sessionId={sessionId} active="practice">
      <div className="mx-auto w-full max-w-6xl px-6 py-10">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <span className="inline-flex rounded-full border border-accent-glow/25 bg-accent-glow/[0.06] px-3 py-1 text-[11px] uppercase tracking-[0.2em] text-accent-glow/75">
              ANIMUS · adaptive practice
            </span>
            <h1 className="mt-4 text-3xl font-semibold tracking-tight">Practice the loop, not the prompt.</h1>
            <p className="mt-2 max-w-2xl text-sm leading-relaxed text-foreground/50">
              Inspect the scene, then answer from memory. Every trial is local, deterministic, and scored
              against the symbolic scene you just saw — never against a hidden neural target.
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
              <div className="flex min-h-[420px] flex-col items-center justify-center p-8 text-center">
                <span className="rounded-full border border-white/10 px-3 py-1 text-[11px] uppercase tracking-[0.18em] text-foreground/40">
                  {session?.title ?? "Loading session"}
                </span>
                <h2 className="mt-4 text-xl font-medium">A short adaptive session</h2>
                <p className="mt-2 max-w-md text-sm leading-relaxed text-foreground/45">
                  The next task is chosen from the dimension with the least evidence, then from expected
                  information gain. Confidence is recorded before feedback so calibration can be estimated
                  separately from reconstruction accuracy.
                </p>
                <Button className="mt-6" onClick={begin} disabled={busy || !session}>
                  {busy ? "Preparing…" : "Start practice"}
                </Button>
              </div>
            ) : phase === "preview" && task ? (
              <div className="relative">
                <AnimusScene
                  scene={session?.scene as StudioSnapshot["scene"]}
                  selectedId={null}
                  onSelect={() => undefined}
                  showOverlay={false}
                  className="h-[420px]"
                />
                <div className="absolute inset-x-0 bottom-0 z-20 flex items-center justify-between gap-3 bg-gradient-to-t from-black/80 to-transparent px-5 pb-5 pt-16">
                  <div>
                    <p className="text-[11px] uppercase tracking-[0.18em] text-accent-glow/70">Inspect</p>
                    <p className="mt-1 text-sm text-foreground/75">
                      Hold the scene in mind. It hides in {task.preview_seconds}s.
                    </p>
                  </div>
                  <Button variant="secondary" onClick={revealQuestion}>
                    Hide and answer
                  </Button>
                </div>
              </div>
            ) : phase === "question" && task ? (
              <div className="p-6">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-[11px] uppercase tracking-[0.18em] text-accent-glow/65">
                    {dimensionLabel(profile, task.dimension)} · difficulty {Math.round(task.difficulty * 100)}%
                  </span>
                  <span className="text-[11px] text-foreground/35">
                    {task.response_kind === "token_selection"
                      ? "Reconstruct the object set"
                      : task.response_kind === "spatial_placement"
                        ? "Reconstruct the layout"
                        : candidateOptions.length
                          ? "Compare the two candidates"
                          : "Choose one option"}
                  </span>
                </div>
                <h2 className="mt-2 text-xl font-medium tracking-tight">{task.prompt}</h2>

                {task.response_kind !== "option" ? (
                  <ReconstructionBoard
                    mode={task.response_kind === "token_selection" ? "select" : "place"}
                    tokens={task.tokens}
                    layout={task.layout}
                    selectedTokenIds={selectedTokens}
                    placements={placements}
                    disabled={busy}
                    onToggle={toggleToken}
                    onPlace={placeToken}
                    onClearPlacements={() => setPlacements([])}
                  />
                ) : candidateOptions.length ? (
                  <div className="mt-5 grid gap-4 md:grid-cols-2">
                    {candidateOptions.map((option) => (
                      <button
                        key={option.id}
                        type="button"
                        onClick={() => setSelected(option.id)}
                        className={`overflow-hidden rounded-xl border text-left transition ${
                          selected === option.id
                            ? "border-accent-glow/70 ring-2 ring-accent-glow/30"
                            : "border-white/10 hover:border-white/25"
                        }`}
                      >
                        {option.scene ? (
                          <SceneSketch
                            scene={option.scene}
                            className="pointer-events-none h-56 w-full"
                            showLabels
                          />
                        ) : null}
                        <div className="flex items-center justify-between px-4 py-3">
                          <span className="text-sm">{option.label}</span>
                          <span className="text-[11px] uppercase tracking-wide text-foreground/35">
                            {selected === option.id ? "Selected" : "Choose"}
                          </span>
                        </div>
                      </button>
                    ))}
                  </div>
                ) : (
                  <div className="mt-5 grid gap-3">
                    {task.options.map((option) => (
                      <button
                        key={option.id}
                        type="button"
                        onClick={() => setSelected(option.id)}
                        className={`rounded-xl border px-4 py-3 text-left text-sm transition ${
                          selected === option.id
                            ? "border-accent-glow/70 bg-accent-glow/[0.08] text-foreground"
                            : "border-white/10 text-foreground/70 hover:border-white/25"
                        }`}
                      >
                        <span className="mr-3 text-[11px] uppercase tracking-wide text-foreground/35">
                          {option.id}
                        </span>
                        {option.label}
                      </button>
                    ))}
                  </div>
                )}

                <div className="mt-6 rounded-xl border border-white/10 bg-white/[0.025] p-4">
                  <div className="flex items-center justify-between gap-4">
                    <label htmlFor="confidence" className="text-xs text-foreground/55">
                      How confident are you?
                    </label>
                    <span className="text-sm tabular-nums text-foreground/70">{confidence}%</span>
                  </div>
                  <input
                    id="confidence"
                    type="range"
                    min={0}
                    max={100}
                    step={5}
                    value={confidence}
                    onChange={(event) => setConfidence(Number(event.target.value))}
                    className="mt-3 w-full accent-[#8ea2ff]"
                  />
                  <p className="mt-2 text-[11px] text-foreground/35">
                    Confidence is scored separately. Being wrong with low confidence is different from being
                    wrong with high confidence.
                  </p>
                </div>

                <Button className="mt-5 w-full" onClick={submit} disabled={!canSubmit || busy}>
                  {busy ? "Scoring locally…" : "Submit answer"}
                </Button>
              </div>
            ) : phase === "feedback" && result ? (
              <div className="flex min-h-[420px] flex-col items-center justify-center p-8 text-center">
                <span
                  className={`rounded-full border px-3 py-1 text-[11px] uppercase tracking-[0.18em] ${
                    result.feedback?.correct
                      ? "border-emerald-300/25 bg-emerald-300/[0.06] text-emerald-200/75"
                      : "border-amber-300/25 bg-amber-300/[0.06] text-amber-200/75"
                  }`}
                >
                  {result.feedback?.correct
                    ? "Correct"
                    : task?.response_kind === "option"
                      ? "Recorded"
                      : "Reconstruction recorded"}
                </span>
                <h2 className="mt-4 text-xl font-medium">
                  {result.feedback?.correct
                    ? "The scene held."
                    : task?.response_kind === "option"
                      ? "A useful error."
                      : "The trace is visible."}
                </h2>
                <p className="mt-2 max-w-md text-sm leading-relaxed text-foreground/50">
                  {result.feedback?.message ??
                    "The trial was recorded locally and added to your behavioural profile."}
                </p>
                {task?.response_kind === "token_selection" ? (
                  <dl className="mt-4 flex flex-wrap justify-center gap-4 text-xs text-foreground/45">
                    <div><dt className="inline">Omissions: </dt><dd className="inline text-foreground/75">{omissions}</dd></div>
                    <div><dt className="inline">Intrusions: </dt><dd className="inline text-foreground/75">{intrusions}</dd></div>
                  </dl>
                ) : null}
                {task?.response_kind === "spatial_placement" ? (
                  <p className="mt-3 text-xs text-foreground/45">
                    Mean spatial error: <span className="text-foreground/75">{meanSpatialError ?? "—"}</span>
                  </p>
                ) : null}
                {!result.feedback?.correct && correctLabel ? (
                  <p className="mt-3 text-xs text-foreground/45">
                    Correct option: <span className="text-foreground/75">{correctLabel}</span>
                  </p>
                ) : null}
                <div className="mt-6 flex flex-wrap justify-center gap-2">
                  <Button onClick={advance}>{nextTask ? "Next trial" : "Start another"}</Button>
                  <Button variant="secondary" onClick={() => router.push("/animus/profile")}>
                    See profile
                  </Button>
                </div>
              </div>
            ) : (
              <div className="flex min-h-[420px] items-center justify-center p-8 text-sm text-foreground/45">
                Preparing the next trial…
              </div>
            )}
          </section>

          <aside className="space-y-4">
            <div className="rounded-2xl border border-white/10 bg-white/[0.025] p-5">
              <p className="text-[11px] uppercase tracking-[0.18em] text-foreground/35">Local profile</p>
              <div className="mt-3 flex items-baseline justify-between">
                <span className="text-sm text-foreground/65">Trials recorded</span>
                <span className="text-2xl font-semibold tabular-nums">{profile?.trial_count ?? 0}</span>
              </div>
              <p className="mt-2 text-[11px] leading-relaxed text-foreground/35">
                The profile is shared across sessions on this machine. Practice never changes the scene.
              </p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/[0.025] p-5">
              <p className="text-[11px] uppercase tracking-[0.18em] text-foreground/35">Why this task</p>
              <p className="mt-2 text-sm text-foreground/75">
                {task ? dimensionLabel(profile, task.dimension) : "Chosen adaptively when you start"}
              </p>
              {adaptive ? (
                <>
                  <p className="mt-2 text-[11px] leading-relaxed text-foreground/45">{adaptive.reason}</p>
                  <p className="mt-2 font-mono text-[11px] uppercase tracking-[0.12em] text-foreground/30">
                    {adaptive.task_type} · difficulty {adaptive.difficulty.toFixed(2)}
                    {typeof adaptive.expected_gain === "number"
                      ? ` · expected gain ${adaptive.expected_gain.toFixed(3)}`
                      : ""}
                  </p>
                </>
              ) : (
                <p className="mt-2 text-[11px] leading-relaxed text-foreground/35">
                  Selection starts with a coverage floor, then favours expected information gain.
                </p>
              )}
              <p className="mt-2 text-[11px] leading-relaxed text-foreground/30">
                Difficulty adjusts after a short rolling window; there is no engagement streak or leaderboard.
              </p>
            </div>
            <div className="rounded-2xl border border-amber-300/15 bg-amber-300/[0.035] p-5">
              <p className="text-[11px] uppercase tracking-[0.18em] text-amber-200/55">Boundary</p>
              <p className="mt-2 text-[11px] leading-relaxed text-foreground/45">
                This is behavioural scene practice, not a diagnosis, treatment, or neural decoder. Stop if
                you feel fatigued or frustrated. Aphantasia is a variation, not a deficit.
              </p>
            </div>
          </aside>
        </div>
      </div>
    </AnimusShell>
  );
}
