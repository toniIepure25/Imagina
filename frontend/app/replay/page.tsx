"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import AppShell from "@/components/layout/AppShell";
import Button from "@/components/common/Button";
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
        <div className="flex-1 flex items-center justify-center p-6">
          <div className="glass panel-glow p-8 text-center space-y-5 max-w-lg">
            <div className="text-[10px] uppercase tracking-[0.2em] text-accent-glow/80">Deterministic Demo</div>
            <h1 className="text-3xl font-bold glow-text">Dream Corridor Replay</h1>
            <p className="text-sm text-foreground/65 leading-relaxed">
              Watch a pre-generated &quot;improving user&quot; demo session with deterministic signals.
              The corridor is adaptive feedback, not decoded imagery.
            </p>
            <Button onClick={startDemo} disabled={loading} size="lg">
              {loading ? "Generating..." : "Start Demo"}
            </Button>
          </div>
        </div>
      ) : (
        <div className="flex-1 flex flex-col min-h-0">
          {sessionId && (
            <div className="px-4 py-3 text-xs text-foreground/50 border-b border-surface-border bg-background/70 backdrop-blur flex flex-wrap items-center gap-3">
              <span className="text-[10px] uppercase tracking-[0.18em] text-accent-glow/80">Replay Phase</span>
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
                <div className="mb-2 text-[10px] uppercase tracking-[0.18em] text-accent-glow/80">Demo Narrative</div>
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
