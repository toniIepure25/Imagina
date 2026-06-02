"use client";

import { useCallback, useState } from "react";
import * as api from "@/lib/imaginaApi";

const DEMO_PROFILES = ["stable_improving", "distracted", "fatigued", "high_vividness", "low_vividness", "noisy"];
const TASKS = [
  "shape_stabilization", "color_stabilization", "brightness_contrast", "motion",
  "object_detail", "spatial_position", "scene_construction", "perspective_viewpoint",
  "multisensory_scene", "symbolic_scene", "stable_return",
];

interface StepResult {
  iqi_score: number; pid_score: number;
  safety_action: string; curriculum_action: string;
  scene_params: Record<string, number>; prompt: string;
  state: Record<string, number>;
  iqi_interpretation?: string; pid_interpretation?: string;
  safety_message?: string; curriculum_message?: string;
}

interface SessionEvent {
  event_id: string; event_type: string; timestamp: string;
  payload: Record<string, unknown>; session_id: string;
}

interface SessionSummary {
  session_id: string; total_steps: number;
  mean_iqi: number; mean_pid: number;
  tasks_completed: string[];
  curriculum_actions: Record<string, number>;
  safety_actions: Record<string, number>;
  disclaimer: string;
}

interface UserProfile {
  user_id: string; session_count: number; total_steps: number;
  mean_iqi: number; mean_pid: number; best_iqi: number; best_pid: number;
  iqi_trend_slope: number; pid_trend_slope: number;
  fatigue_trend_slope: number;
  best_tasks: string[]; level_success_rates: Record<string, number>;
  optimal_session_length_steps: number | null;
  fatigue_threshold_estimate: number | null;
  recommendations: Recommendation[];
}

interface Recommendation {
  type: string; priority: string; message: string; reason: string;
  next_task_id?: string;
}

interface SessionAnalytics {
  session_id: string; n_steps: number;
  mean_iqi: number; mean_pid: number;
  best_iqi: number; best_step: number;
  iqi_slope: number; pid_slope: number; fatigue_slope: number;
  interpretation: string;
}

export function useImaginaSession() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [demoProfile, setDemoProfile] = useState("stable_improving");
  const [taskId, setTaskId] = useState("shape_stabilization");
  const [lastStep, setLastStep] = useState<StepResult | null>(null);
  const [events, setEvents] = useState<SessionEvent[]>([]);
  const [summary, setSummary] = useState<SessionSummary | null>(null);
  const [profile, setProfileState] = useState<UserProfile | null>(null);
  const [analytics, setAnalytics] = useState<SessionAnalytics | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const userId = "default";

  const clearError = () => setError(null);

  const start = useCallback(async () => {
    setLoading(true); clearError();
    try {
      const r = await api.startSession({ demo_mode: true, demo_profile: demoProfile });
      setSessionId(r.session_id as string);
    } catch (e: unknown) { setError(e instanceof Error ? e.message : "Unknown error"); }
    setLoading(false);
  }, [demoProfile]);

  const startT = useCallback(async () => {
    if (!sessionId) return;
    setLoading(true);
    try { await api.startTask(sessionId, taskId); } catch (e: unknown) { setError(e instanceof Error ? e.message : "Unknown error"); }
    setLoading(false);
  }, [sessionId, taskId]);

  const submitSR = useCallback(async (vals: { vividness: number; stability: number; effort: number; fatigue: number; comfort: number }) => {
    if (!sessionId) return;
    setLoading(true);
    try { await api.submitSelfReport(sessionId, { ...vals, task_id: taskId }); }
    catch (e: unknown) { setError(e instanceof Error ? e.message : "Unknown error"); }
    setLoading(false);
  }, [sessionId, taskId]);

  const step = useCallback(async () => {
    if (!sessionId) return;
    setLoading(true);
    try {
      const r = await api.runStep(sessionId);
      setLastStep(r as StepResult);
    } catch (e: unknown) { setError(e instanceof Error ? e.message : "Unknown error"); }
    setLoading(false);
  }, [sessionId]);

  const refresh = useCallback(async () => {
    if (!sessionId) return;
    try {
      const [es, sm] = await Promise.all([
        api.getEvents(sessionId) as Promise<{ events: SessionEvent[]; event_count: number }>,
        api.getSummary(sessionId) as Promise<SessionSummary>,
      ]);
      setEvents(es.events || []);
      setSummary(sm);
    } catch (e: unknown) { setError(e instanceof Error ? e.message : "Unknown error"); }
  }, [sessionId]);

  const loadProfile = useCallback(async () => {
    try { setProfileState(await api.getProfile(userId)); } catch { /silent/ }
  }, []);

  const updateProfile = useCallback(async () => {
    if (!sessionId) return;
    try { setProfileState(await api.updateProfileFromSession(userId, sessionId)); } catch { /silent/ }
  }, [sessionId]);

  const resetProfile = useCallback(async () => {
    try { setProfileState(await api.resetProfile(userId)); } catch { /silent/ }
  }, []);

  const loadAnalytics = useCallback(async () => {
    if (!sessionId) return;
    try { setAnalytics(await api.getSessionAnalytics(sessionId)); } catch { /silent/ }
  }, [sessionId]);

  const loadRecs = useCallback(async () => {
    if (!sessionId) return;
    try { setProfileState(await api.getProfile(userId)); } catch { /silent/ }
  }, [sessionId]);

  const reset = useCallback(() => {
    setSessionId(null); setLastStep(null); setEvents([]);
    setSummary(null); setAnalytics(null); setProfileState(null); setError(null);
  }, []);

  return {
    sessionId, profile, taskId, lastStep, events, summary, analytics, loading, error,
    demoProfile, setDemoProfile, setTaskId,
    start, startT, submitSR, step, refresh, reset,
    loadProfile, updateProfile, resetProfile, loadAnalytics, loadRecs,
    DEMO_PROFILES, TASKS,
  };
}
