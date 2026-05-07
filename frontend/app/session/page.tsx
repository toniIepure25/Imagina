"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import AppShell from "@/components/layout/AppShell";
import SessionSetup from "@/components/session/SessionSetup";
import BaselineCalibration from "@/components/session/BaselineCalibration";
import SelfReportPanel from "@/components/session/SelfReportPanel";
import GuidedPromptPanel from "@/components/session/GuidedPromptPanel";
import SessionControls from "@/components/session/SessionControls";
import SessionSummaryCard from "@/components/session/SessionSummaryCard";
import MetricsDashboard from "@/components/metrics/MetricsDashboard";
import CurriculumTimeline from "@/components/metrics/CurriculumTimeline";
import SafetyBanner from "@/components/metrics/SafetyBanner";
import { ImaginaSocket } from "@/lib/websocket";
import { apiFetch } from "@/lib/api";
import { feedbackToScene, DEFAULT_SCENE_PARAMS, SceneParams } from "@/lib/feedbackMapping";
import type { CalibrationProfile, FeedbackAction, SafetyEvent, SessionSummary, WSMessage, Session } from "@/lib/types";

const DreamCorridorScene = dynamic(() => import("@/components/scene/DreamCorridorScene"), { ssr: false });

type Phase = "setup" | "calibration" | "running" | "summary";

export default function SessionPage() {
  const [phase, setPhase] = useState<Phase>("setup");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sceneParams, setSceneParams] = useState<SceneParams>(DEFAULT_SCENE_PARAMS);
  const [promptText, setPromptText] = useState("");
  const [iqi, setIqi] = useState(0);
  const [pid, setPid] = useState(0.5);
  const [attention, setAttention] = useState(0);
  const [fatigue, setFatigue] = useState(0);
  const [uncertainty, setUncertainty] = useState(0);
  const [interpretation, setInterpretation] = useState("unknown");
  const [level, setLevel] = useState(1);
  const [levelName, setLevelName] = useState("Breath + Fixation");
  const [taskName, setTaskName] = useState("Dream Corridor Stabilization");
  const [timeline, setTimeline] = useState<{ window: number; iqi: number; pid: number; attention: number; fatigue: number }[]>([]);
  const [safetyEvents, setSafetyEvents] = useState<SafetyEvent[]>([]);
  const [summary, setSummary] = useState<SessionSummary | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [wsStatus, setWsStatus] = useState("disconnected");
  const [signalProviderId, setSignalProviderId] = useState("simulated.default");
  const [scenario, setScenario] = useState("improving_user");
  const [experimentRunId, setExperimentRunId] = useState<string | null>(() => {
    if (typeof window === "undefined") return null;
    return new URLSearchParams(window.location.search).get("experimentRunId");
  });
  const [calibration, setCalibration] = useState<CalibrationProfile | null>(null);

  const socketRef = useRef<ImaginaSocket | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const baselineRef = useRef<Record<string, number> | null>(null);

  const handleStop = useCallback(async (sendStop = true) => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (sendStop) socketRef.current?.send("stop_session");
    if (sessionId) {
      try {
        await apiFetch(`/api/sessions/${sessionId}/stop`, { method: "POST" });
      } catch { /* may already be stopped */ }
      try {
        const summary = await apiFetch<SessionSummary>(`/api/sessions/${sessionId}/summary`);
        setSummary(summary);
      } catch { /* summary not available yet */ }
    }
    socketRef.current?.disconnect();
    setPhase("summary");
  }, [sessionId]);

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
        break;
      case "pid_update":
        setPid(p.pid as number);
        setInterpretation(p.interpretation as string);
        break;
      case "state_estimate":
        setAttention(p.attention_stability as number);
        setFatigue(p.fatigue as number);
        setUncertainty(p.uncertainty as number);
        setTimeline((prev) => [
          ...prev,
          {
            window: prev.length,
            iqi: p.attention_stability as number,
            pid: 0,
            attention: p.attention_stability as number,
            fatigue: p.fatigue as number,
          },
        ]);
        break;
      case "curriculum_update":
        setLevel(p.current_level as number);
        setLevelName(p.level_name as string);
        break;
      case "safety_event":
        setSafetyEvents((prev) => [...prev, p as unknown as SafetyEvent]);
        break;
      case "session_stopped":
        handleStop(false);
        break;
    }

    if (msg.type === "iqi_update" || msg.type === "pid_update") {
      setTimeline((prev) => {
        const last = prev[prev.length - 1];
        if (!last) return prev;
        const updated = { ...last };
        if (msg.type === "iqi_update") updated.iqi = p.iqi as number;
        if (msg.type === "pid_update") updated.pid = p.pid as number;
        return [...prev.slice(0, -1), updated];
      });
    }
  }, [handleStop]);

  const handleSetup = async (config: {
    displayName: string;
    taskId: string;
    mode: string;
    userId: string | null;
    signalProviderId: string;
    scenario: string;
    experimentRunId: string | null;
  }) => {
    if (config.mode === "replay") {
      window.location.href = "/replay";
      return;
    }
    setSignalProviderId(config.signalProviderId);
    setScenario(config.scenario);
    setExperimentRunId(config.experimentRunId);
    const session = await apiFetch<Session>("/api/sessions", {
      method: "POST",
      body: JSON.stringify({
        user_id: config.userId,
        display_name: config.displayName,
        task_id: config.taskId,
        mode: "simulated",
        signal_provider_id: config.signalProviderId,
        scenario: config.scenario,
        experiment_run_id: config.experimentRunId,
        safety_disclaimer_acknowledged: true,
      }),
    });
    setTaskName(config.taskId === "corridor_doors" ? "Corridor With Doors" : config.taskId === "memory_room" ? "Memory Room Return" : "Simple Corridor Stabilization");
    setSessionId(session.session_id);
    setPhase("calibration");
  };

  const handleBaseline = async (
    baseline: { focus: number; relaxation: number; vividness: number; fatigue: number },
    calibrationProfile: CalibrationProfile,
  ) => {
    if (!sessionId) return;
    baselineRef.current = baseline;
    setCalibration(calibrationProfile);
    await apiFetch(`/api/sessions/${sessionId}/start`, { method: "POST" });

    const sock = new ImaginaSocket(sessionId);
    sock.onMessage(handleMessage);
    sock.onStatus(setWsStatus);
    sock.connect();
    socketRef.current = sock;

    setTimeout(() => {
      sock.send("start_session", { baseline, scenario, seed: 42 });
    }, 500);

    timerRef.current = setInterval(() => setElapsed((e) => e + 1), 1000);
    setPhase("running");
  };

  const handleSelfReport = async (report: Record<string, unknown>) => {
    if (!sessionId) return;
    socketRef.current?.send("self_report", { payload: report });
    await apiFetch(`/api/sessions/${sessionId}/self-report`, {
      method: "POST",
      body: JSON.stringify(report),
    });
  };

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const existingSessionId = params.get("sessionId");
    if (existingSessionId) {
      apiFetch<Session>(`/api/sessions/${existingSessionId}`).then((session) => {
        setSessionId(session.session_id);
        setSignalProviderId(session.signal_provider_id);
        setScenario(session.scenario || "improving_user");
        setExperimentRunId(session.experiment_run_id);
        setTaskName(session.task_id === "corridor_doors" ? "Corridor With Doors" : session.task_id === "memory_room" ? "Memory Room Return" : "Simple Corridor Stabilization");
        setPhase("calibration");
      }).catch(() => setPhase("setup"));
    }
    return () => {
      socketRef.current?.disconnect();
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  if (phase === "setup") {
    return (
      <AppShell>
        <div className="flex-1 flex items-center justify-center">
          <SessionSetup experimentRunId={experimentRunId} onStart={handleSetup} />
        </div>
      </AppShell>
    );
  }

  if (phase === "calibration") {
    return (
      <AppShell>
        <div className="flex-1 flex items-center justify-center">
          {sessionId && (
            <BaselineCalibration
              sessionId={sessionId}
              providerId={signalProviderId}
              onComplete={handleBaseline}
            />
          )}
        </div>
      </AppShell>
    );
  }

  if (phase === "summary") {
    return (
      <AppShell>
        <div className="flex-1 flex items-center justify-center p-8">
          {summary ? (
            <SessionSummaryCard summary={summary} />
          ) : (
            <div className="glass p-8 text-center space-y-4">
              <h2 className="text-xl font-bold">Session Ended</h2>
              <p className="text-foreground/60 text-sm">
                Duration: {Math.floor(elapsed / 60)}m {elapsed % 60}s | Windows: {timeline.length}
              </p>
              <Link href="/" className="text-accent text-sm hover:underline">Back to Home</Link>
            </div>
          )}
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell level={level} status={wsStatus}>
      <div className="flex-1 flex flex-col min-h-0">
        <SessionControls
          status="running"
          elapsed={elapsed}
          level={level}
          levelName={levelName}
          mode="Simulated V1"
          taskName={taskName}
          connectionStatus={wsStatus}
          onStop={() => handleStop()}
        />
        <CurriculumTimeline currentLevel={level} />
        <SafetyBanner events={safetyEvents} />
        <div className="flex-1 min-h-0 flex flex-col xl:flex-row">
          <div className="flex-1 min-h-[460px] xl:min-h-0 relative">
            <DreamCorridorScene params={sceneParams} />
          </div>
          <div className="w-full xl:w-[380px] border-l border-surface-border overflow-y-auto bg-background/68 backdrop-blur-md">
            <GuidedPromptPanel text={promptText} />
            {calibration && (
              <div className="mx-4 mt-4 rounded-lg border border-accent/20 bg-accent/8 p-3 text-xs text-foreground/55">
                Calibration quality <span className="font-mono text-accent-glow">{Math.round(calibration.calibration_quality_score * 100)}%</span>
                {experimentRunId && <span> | Experiment-linked</span>}
              </div>
            )}
            <MetricsDashboard
              iqi={iqi}
              pid={pid}
              attention={attention}
              fatigue={fatigue}
              uncertainty={uncertainty}
              interpretation={interpretation}
              timeline={timeline}
            />
            <SelfReportPanel onSubmit={handleSelfReport} />
          </div>
        </div>
      </div>
    </AppShell>
  );
}
