"use client";

import { useState, useCallback } from "react";

interface BuiltinPolicy { policy_id: string; title: string; payload: Record<string, unknown>; }
interface Profile { policy_id: string; title?: string; origin?: string; payload?: { policy_type?: string; title?: string }; }
interface Matrix { ranked_policies: Array<{ rank: number; policy_id: string; title?: string; grade?: string; score: number }>; best_policy_id: string; }
interface Leaderboard { category_winners: Record<string, string>; tradeoff_summary: string; }

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

async function api(path: string, method = "GET", body?: unknown) {
  const r = await fetch(`${API_BASE}${path}`, {
    method, headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!r.ok) throw new Error(`${method} ${path} failed`);
  return r.json();
}

export function useAdaptivePolicyLab(userId = "demo_user") {
  const [builtins, setBuiltins] = useState<BuiltinPolicy[]>([]);
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [editorPayload, setEditorPayload] = useState<Record<string, unknown>>({});
  const [validationResult, setValidationResult] = useState<Record<string, unknown> | null>(null);
  const [latestMatrix, setLatestMatrix] = useState<Matrix | null>(null);
  const [latestLeaderboard, setLatestLeaderboard] = useState<Leaderboard | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const loadBuiltins = useCallback(async () => {
    try { const r = await api("/api/imagina/policy-lab/builtins"); setBuiltins(r.policies || []); } catch { setError("Failed to load builtins"); }
  }, []);

  const loadExample = useCallback(async (): Promise<Record<string, unknown>> => {
    try { const r = await api("/api/imagina/policy-lab/example"); return r; } catch { return {}; }
  }, []);

  const loadProfiles = useCallback(async () => {
    try { const r = await api(`/api/imagina/policy-lab/profiles/${userId}`); setProfiles(r.policies || []); } catch { setProfiles([]); }
  }, [userId]);

  const validateEditorPayload = useCallback(async () => {
    try { const r = await api("/api/imagina/policy-lab/validate", "POST", editorPayload); setValidationResult(r); return r; } catch { const rv = { valid: false, quality_score: 0 } as Record<string, unknown>; setValidationResult(rv); return rv; }
  }, [editorPayload]);

  const importEditorPayload = useCallback(async (allowDraft = false) => {
    setLoading(true);
    try { await api(`/api/imagina/policy-lab/import/${userId}`, "POST", editorPayload); await loadProfiles(); } catch { setError("Import failed"); }
    setLoading(false);
  }, [editorPayload, userId, loadProfiles]);

  const runPolicy = useCallback(async (policyId: string) => {
    setLoading(true);
    try { return await api(`/api/imagina/policy-lab/run/${userId}/${policyId}`, "POST"); } catch { setError(`Benchmark failed for ${policyId}`); return null; } finally { setLoading(false); }
  }, [userId]);

  const runMatrix = useCallback(async (policyIds?: string[]) => {
    setLoading(true);
    try { const r = await api(`/api/imagina/policy-lab/run-matrix/${userId}`, "POST", { policy_ids: policyIds }); setLatestMatrix(r); return r; } catch { setError("Matrix failed"); return null; } finally { setLoading(false); }
  }, [userId]);

  const loadLatestMatrix = useCallback(async () => {
    try { const r = await api(`/api/imagina/policy-lab/latest-matrix/${userId}`); setLatestMatrix(r); } catch { setError("No matrix found"); }
  }, [userId]);

  const buildLeaderboard = useCallback(async () => {
    try { const r = await api(`/api/imagina/policy-lab/leaderboard/${userId}`, "POST"); setLatestLeaderboard(r); return r; } catch { setError("Leaderboard failed"); return null; }
  }, [userId]);

  const loadLeaderboard = useCallback(async () => {
    try { const r = await api(`/api/imagina/policy-lab/leaderboard/${userId}`); setLatestLeaderboard(r); } catch { setError("No leaderboard found"); }
  }, [userId]);

  const exportPolicyLab = useCallback(async () => {
    try { return await api(`/api/imagina/policy-lab/export/${userId}`, "POST"); } catch { setError("Export failed"); return null; }
  }, [userId]);

  const refreshAll = useCallback(async () => {
    await Promise.all([loadBuiltins(), loadProfiles()]);
    try { await loadLatestMatrix(); } catch { /* no matrix yet */ }
    try { await loadLeaderboard(); } catch { /* no leaderboard yet */ }
  }, [loadBuiltins, loadProfiles, loadLatestMatrix, loadLeaderboard]);

  return { builtins, profiles, editorPayload, setEditorPayload, validationResult, latestMatrix, latestLeaderboard,
           loading, error, loadBuiltins, loadExample, loadProfiles, validateEditorPayload, importEditorPayload,
           runPolicy, runMatrix, loadLatestMatrix, buildLeaderboard, loadLeaderboard, exportPolicyLab, refreshAll };
}
