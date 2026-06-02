"use client";

import { useState, useCallback } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

async function api(path: string, method = "GET", body?: unknown) {
  const r = await fetch(`${API_BASE}${path}`, {
    method, headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!r.ok) throw new Error(`${method} ${path} failed`);
  return r.json();
}

export function useCapstoneDemo(userId = "demo_user") {
  const [latestDemo, setLatestDemo] = useState<Record<string, unknown> | null>(null);
  const [evidencePack, setEvidencePack] = useState<Record<string, unknown> | null>(null);
  const [narrative, setNarrative] = useState<Record<string, unknown> | null>(null);
  const [readiness, setReadiness] = useState<Record<string, unknown> | null>(null);
  const [boundaries, setBoundaries] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const runDemo = useCallback(async () => {
    setLoading(true); setError("");
    try { const r = await api(`/api/imagina/capstone/demo/${userId}/run`, "POST"); setLatestDemo(r); return r; }
    catch (e) { setError(String(e)); return null; }
    finally { setLoading(false); }
  }, [userId]);

  const buildEvidencePack = useCallback(async () => {
    try { const r = await api(`/api/imagina/capstone/evidence-pack/${userId}`, "POST"); setEvidencePack(r); return r; }
    catch (e) { setError(String(e)); return null; }
  }, [userId]);

  const buildNarrative = useCallback(async () => {
    try { const r = await api(`/api/imagina/capstone/narrative/${userId}`, "POST"); setNarrative(r); return r; }
    catch (e) { setError(String(e)); return null; }
  }, [userId]);

  const checkReadiness = useCallback(async () => {
    try { const r = await api(`/api/imagina/capstone/readiness/${userId}`, "POST"); setReadiness(r); return r; }
    catch (e) { setError(String(e)); return null; }
  }, [userId]);

  const loadBoundaries = useCallback(async () => {
    try { const r = await api("/api/imagina/capstone/boundaries"); setBoundaries(r); }
    catch { /* optional */ }
  }, []);

  const refreshAll = useCallback(async () => {
    try { const r = await api(`/api/imagina/capstone/demo/${userId}/latest`); setLatestDemo(r); } catch { /* no demo */ }
    try { await api(`/api/imagina/capstone/evidence-pack/${userId}/latest`); } catch { /* no pack */ }
    try { const r = await api(`/api/imagina/capstone/readiness/${userId}`); setReadiness(r); } catch { /* no readiness */ }
    await loadBoundaries();
  }, [userId, loadBoundaries]);

  return { latestDemo, evidencePack, narrative, readiness, boundaries, loading, error,
           runDemo, buildEvidencePack, buildNarrative, checkReadiness, loadBoundaries, refreshAll };
}
