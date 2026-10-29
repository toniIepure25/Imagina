"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import AppShell from "@/components/layout/AppShell";
import Button from "@/components/common/Button";
import PageHeader from "@/components/platform/PageHeader";
import BoundaryNote from "@/components/platform/BoundaryNote";
import MetricsDashboard from "@/components/metrics/MetricsDashboard";
import CurriculumTimeline from "@/components/metrics/CurriculumTimeline";
import GuidedPromptPanel from "@/components/session/GuidedPromptPanel";
import { ImaginaSocket } from "@/lib/websocket";
import { apiFetch } from "@/lib/api";
import { feedbackToScene, DEFAULT_SCENE_PARAMS, SceneParams } from "@/lib/feedbackMapping";
import type { FeedbackAction, WSMessage } from "@/lib/types";

const DreamCorridorScene = dynamic(() => import("@/components/scene/DreamCorridorScene"), { ssr: false });

function replayPhase(windowCount: number, level: number, iqi: number, pid: number) {
  if (windowCount === 0) return "Calibration";
  if (windowCount < 6 || pid > 0.55) return "Early instability";
  if (level < 4 || iqi < 0.62) return "Stabilization";
  if (level >= 6) return "Detail unlock";
  return "Cooldown / Summary";
}

const NARRATIVE = [
  "Unstable corridor at start",
  "Attention proxy stabilizes",
  "PID proxy decreases",
  "IQI proxy increases",
  "Corridor becomes clearer",
  "Doors and details unlock",
  "Report summarizes the session",
];

export default function ReplayPage() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [paused, setPaused] = useState(false);
  const [sceneParams, setSceneParams] = useState<SceneParams>(DEFAULT_SCENE_PARAMS);
  const [promptText, setPromptText] = useState("");
  const [iqi, setIqi] = useState(0);
  const [pid, setPid] = useState(0.5);
  const [attention, setAttention] = useState(0);
  const [fatigue, setFatigue] = useState(0);
  const [uncertainty, setUncertainty] = useState(0);
  const [interpretation, setInterpretation] = useState("unknown");
  const [level, setLevel] = useState(1);
  const [timeline, setTimeline] = useState<{ window: number; iqi: number; pid: number; attention: number; fatigue: number }[]>([]);
  const [error, setError] = useState<string | null>(null);

  const socketRef = useRef<ImaginaSocket | null>(null);
  const phase = replayPhase(timeline.length, level, iqi, pid);

  const resetReplay = useCallback(() => {
    socketRef.current?.send("stop_replay");
    socketRef.current?.disconnect();
    socketRef.current = null;
    setSessionId(null);
    setPlaying(false);
    setPaused(false);
    setSceneParams(DEFAULT_SCENE_PARAMS);
    setPromptText("");
    setIqi(0);
    setPid(0.5);
    setAttention(0);
    setFatigue(0);
    setUncertainty(0);
    setInterpretation("unknown");
    setLevel(1);
    setTimeline([]);
  }, []);

  const handleMessage = useCallback((msg: WSMessage) => {
    const p = msg.payload as Record<string, unknown>;
    switch (msg.type) {
      case "feedback_action": {
        const fb = p as unknown as FeedbackAction;
        setSceneParams(feedbackToScene(fb));
        setPromptText(fb.prompt_text);
        break;
      }
      case "iqi_update":
        setIqi(p.iqi as number);
        setTimeline((prev) => {
          const last = prev[prev.length - 1];
          if (last) return [...prev.slice(0, -1), { ...last, iqi: p.iqi as number }];
          return prev;
        });
        break;
      case "pid_update":
        setPid(p.pid as number);
        setInterpretation(p.interpretation as string);
        setTimeline((prev) => {
          const last = prev[prev.length - 1];
          if (last) return [...prev.slice(0, -1), { ...last, pid: p.pid as number }];
          return prev;
        });
        break;
      case "state_estimate":
        setAttention(p.attention_stability as number);
        setFatigue(p.fatigue as number);
        setUncertainty(p.uncertainty as number);
        setTimeline((prev) => [
          ...prev,
          { window: prev.length, iqi, pid, attention: p.attention_stability as number, fatigue: p.fatigue as number },
        ]);
        break;
      case "curriculum_update":
        setLevel(p.current_level as number);
        break;
    }
  }, [iqi, pid]);

  const startDemo = async () => {
    resetReplay();
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch<{ session_id: string }>("/api/replay/demo", { method: "POST" });
      const sid = res.session_id;
      setSessionId(sid);

      const sock = new ImaginaSocket(sid);
      sock.onMessage(handleMessage);
      sock.connect();
      socketRef.current = sock;

      setTimeout(() => {
        sock.send("start_replay", { speed: 2.0 });
        setPlaying(true);
      }, 500);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The replay demo could not be generated.");
    } finally {
      setLoading(false);
    }
  };

  const togglePause = () => {
    if (paused) {
      socketRef.current?.send("resume_replay");
      setPaused(false);
    } else {
      socketRef.current?.send("pause_replay");
      setPaused(true);
    }
  };

  const restartDemo = () => {
    resetReplay();
    void startDemo();
  };

  useEffect(() => () => socketRef.current?.disconnect(), []);

  return (
    <AppShell level={level} status={playing ? (paused ? "paused" : "replaying") : undefined}>
      {!playing ? (
        <div className="mx-auto grid w-full max-w-5xl gap-5 px-4 py-10 md:px-6 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)] lg:items-start">
          <div>
            <PageHeader
              eyebrow="Deterministic demo"
              title="Dream Corridor replay"
              description="Watch a pre-generated improving-user session with deterministic signals. The corridor is adaptive feedback, not decoded imagery, and the replay is the same on every run."
            />
            <div className="mt-5 rounded-xl border border-white/10 bg-white/[0.025] p-5">
              <h2 className="text-lg font-semibold text-foreground/85">What this replay demonstrates</h2>
              <ul className="mt-3 space-y-2 text-sm leading-6 text-foreground/55">
                <li>· A full closed loop from simulated signal to scene parameter.</li>
                <li>· Curriculum progression, proxy metrics, and safety events in one timeline.</li>
                <li>· Deterministic reproducibility: no hidden model, no external service.</li>
              </ul>
              <div className="mt-5 flex flex-wrap items-center gap-2">
                <Button onClick={startDemo} disabled={loading} size="lg">
                  {loading ? "Generating…" : "Start replay"}
                </Button>
                <Link
                  href="/science"
                  className="inline-flex min-h-11 items-center rounded-lg px-3 text-sm text-foreground/55 hover:text-foreground"
                >
                  Read boundaries
                </Link>
              </div>
              {error ? (
                <p role="alert" className="mt-3 rounded-lg border border-danger/25 bg-danger/[0.06] px-3 py-2 text-xs text-danger/85">
                  {error}
                </p>
              ) : null}
            </div>
          </div>
          <aside className="space-y-3">
            <div className="rounded-xl border border-white/10 bg-white/[0.025] p-4">
              <p className="mono-label text-foreground/40">Narrative beats</p>
              <ol className="mt-3 space-y-2">
                {NARRATIVE.map((item, index) => (
                  <li key={item} className="flex gap-2.5 text-xs leading-5 text-foreground/55">
                    <span className="font-mono text-[11px] text-accent-glow/60">{String(index + 1).padStart(2, "0")}</span>
                    {item}
                  </li>
                ))}
              </ol>
            </div>
            <BoundaryNote>
              The replay is a deterministic demonstration of the engineering loop. It is not evidence that the proxy
              metrics track a person&apos;s imagery, and it does not reconstruct mental content.
            </BoundaryNote>
          </aside>
        </div>
      ) : (
        <div className="flex-1 flex flex-col min-h-0">
          {sessionId && (
            <div className="px-4 py-3 text-xs text-foreground/50 border-b border-surface-border bg-background/70 backdrop-blur flex flex-wrap items-center gap-3">
              <span className="text-[11px] uppercase tracking-[0.18em] text-accent-glow/80">Replay Phase</span>
              <span className="text-foreground/85 font-semibold">{phase}</span>
              <span className="font-mono text-foreground/35">session {sessionId.slice(0, 8)}</span>
              <div className="flex-1" />
              <Button variant="secondary" size="sm" onClick={togglePause}>{paused ? "Resume" : "Pause"}</Button>
              <Button variant="ghost" size="sm" onClick={restartDemo}>Restart</Button>
            </div>
          )}
          <CurriculumTimeline currentLevel={level} />
          <div className="flex-1 min-h-0 flex flex-col xl:flex-row">
            <div className="flex-1 min-h-[460px] relative">
              <DreamCorridorScene params={sceneParams} />
            </div>
            <div className="w-full xl:w-[390px] border-l border-surface-border overflow-y-auto bg-background/68 backdrop-blur-md">
              <div className="glass m-3 p-4 panel-glow">
                <div className="mb-2 text-[11px] uppercase tracking-[0.18em] text-accent-glow/80">Demo Narrative</div>
                <ol className="space-y-2 text-xs text-foreground/62">
                  {NARRATIVE.map((item, index) => (
                    <li key={item} className={`flex gap-2 ${index < Math.min(NARRATIVE.length, Math.max(1, Math.ceil(timeline.length / 4))) ? "text-foreground/88" : ""}`}>
                      <span className="font-mono text-accent-glow">{index + 1}</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ol>
              </div>
              <GuidedPromptPanel text={promptText} />
              <MetricsDashboard
                iqi={iqi}
                pid={pid}
                attention={attention}
                fatigue={fatigue}
                uncertainty={uncertainty}
                interpretation={interpretation}
                timeline={timeline}
              />
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
}
