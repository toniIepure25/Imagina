"use client";

import { useState, useRef } from "react";

interface LiveFrame {
  sqi: number; gate_state: string; adaptive_state: string;
  state_confidence: number; policy_action: string;
  scene_policy: Record<string, number>; safety_policy: Record<string, boolean | string>;
  raw_eeg_included: boolean;
}

interface LiveSummary { n_events: number; latest_adaptive_state: string; latest_policy_action: string; }

const API = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

async function api(path: string, method = "GET", body?: unknown) {
  const r = await fetch(`${API}${path}`, {
    method, headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!r.ok) throw new Error(`${method} ${path} failed`);
  return r.json();
}

export function useLiveNeuroadaptiveDemo(userId = "demo_user") {
  const [liveSession, setLiveSession] = useState<Record<string, unknown> | null>(null);
  const [latestFrame, setLatestFrame] = useState<LiveFrame | null>(null);
  const [events, setEvents] = useState<Array<{ event_type?: string; payload?: unknown }>>([]);
  const [summary, setSummary] = useState<LiveSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [autoPoll, setAutoPoll] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refresh = async () => {
    try {
      const s = await api(`/api/imagina/live/summary/${userId}`);
      setSummary(s);
      const ev = await api(`/api/imagina/live/events/${userId}`);
      setEvents((ev.events || []).slice(-30));
      if (liveSession?.live_session_id) {
        const ls = await api(`/api/imagina/live/demo/${liveSession.live_session_id}`);
        setLiveSession(ls);
        if (ls?.frames?.length) setLatestFrame(ls.frames[ls.frames.length - 1] as LiveFrame);
      }
    } catch (e) {
      setError(String(e));
    }
  };

  const startDemo = async (taskId = "red_circle_vividness") => {
    setLoading(true); setError("");
    try {
      const live = await api(`/api/imagina/live/demo/${userId}/start`, "POST", { task_id: taskId });
      setLiveSession(live);
    } catch (e) { setError(String(e)); }
    setLoading(false);
  };

  const stepDemo = async () => {
    if (!liveSession?.live_session_id) return;
    try {
      const frame = await api(`/api/imagina/live/demo/${liveSession.live_session_id}/step`, "POST");
      setLatestFrame(frame);
      await refresh();
    } catch (e) { setError(String(e)); }
  };

  const submitCheckin = async (payload: Record<string, number>) => {
    if (!liveSession?.live_session_id) return;
    try {
      await api(`/api/imagina/live/demo/${liveSession.live_session_id}/checkin`, "POST", payload);
      await refresh();
    } catch (e) { setError(String(e)); }
  };

  const completeDemo = async () => {
    if (!liveSession?.live_session_id) return;
    try {
      await api(`/api/imagina/live/demo/${liveSession.live_session_id}/complete`, "POST");
      setLiveSession(null);
      setLatestFrame(null);
      await refresh();
    } catch (e) { setError(String(e)); }
  };

  const abortDemo = async (reason = "") => {
    if (!liveSession?.live_session_id) return;
    try {
      await api(`/api/imagina/live/demo/${liveSession.live_session_id}/abort`, "POST", { reason });
      setLiveSession(null);
      setLatestFrame(null);
      await refresh();
    } catch (e) { setError(String(e)); }
  };

  const exportDemo = async () => {
    try {
      return await api(`/api/imagina/live/export-safe/${userId}`, "POST", { live_session_id: liveSession?.live_session_id });
    } catch (e) { setError(String(e)); return null; }
  };

  return { liveSession, latestFrame, events, summary, loading, error, autoPoll,
           setAutoPoll, startDemo, stepDemo, submitCheckin, completeDemo, abortDemo, exportDemo, refresh };
}
