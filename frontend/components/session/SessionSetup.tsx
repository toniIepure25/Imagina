"use client";

import { useEffect, useState } from "react";
import Button from "../common/Button";
import DisclaimerBox from "../common/DisclaimerBox";
import { apiFetch } from "@/lib/api";
import type { ImageryProfile, SignalProviderInfo } from "@/lib/types";

const TASKS = [
  { id: "corridor_simple", name: "Simple Corridor Stabilization", desc: "Imagine and stabilize a simple corridor." },
  { id: "corridor_doors", name: "Corridor With Doors", desc: "Stabilize a corridor with doors on either side." },
  { id: "memory_room", name: "Memory Room Return", desc: "Enter a door and stabilize a familiar room." },
];

const MODES = [
  { id: "simulated", name: "Guided (Simulated Signals)" },
  { id: "replay", name: "Replay Demo Session" },
];

const SCENARIOS = [
  { id: "improving_user", name: "Improving user" },
  { id: "unstable_user", name: "Unstable user" },
  { id: "fatigue_after_half", name: "Fatigue after half" },
  { id: "noisy_signal", name: "Noisy signal" },
  { id: "high_vividness_low_stability", name: "High vividness, low stability" },
  { id: "low_vividness_improving", name: "Low vividness improving" },
];

interface Props {
  experimentRunId?: string | null;
  onStart: (config: {
    displayName: string;
    taskId: string;
    mode: string;
    userId: string | null;
    signalProviderId: string;
    scenario: string;
    experimentRunId: string | null;
  }) => void;
}

export default function SessionSetup({ experimentRunId = null, onStart }: Props) {
  const [name, setName] = useState("");
  const [taskId, setTaskId] = useState("corridor_simple");
  const [mode, setMode] = useState("simulated");
  const [profile, setProfile] = useState<ImageryProfile | null>(null);
  const [providers, setProviders] = useState<SignalProviderInfo[]>([]);
  const [signalProviderId, setSignalProviderId] = useState("simulated.default");
  const [scenario, setScenario] = useState("improving_user");
  const [consent, setConsent] = useState(false);
  const [profileLoading, setProfileLoading] = useState(false);

  useEffect(() => {
    apiFetch<SignalProviderInfo[]>("/api/signals/providers").then(setProviders).catch(() => setProviders([]));
    const userId = window.localStorage.getItem("imagina_user_id");
    if (userId) {
      apiFetch<ImageryProfile>(`/api/users/${userId}/profile`).then(setProfile).catch(() => {
        window.localStorage.removeItem("imagina_user_id");
      });
    }
  }, []);

  const createProfile = async () => {
    setProfileLoading(true);
    try {
      const created = await apiFetch<ImageryProfile>("/api/users/local", {
        method: "POST",
        body: JSON.stringify({ display_name: name || "Local Research User", preferred_task_type: taskId }),
      });
      window.localStorage.setItem("imagina_user_id", created.user_id);
      setProfile(created);
    } finally {
      setProfileLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6 p-6">
      <h2 className="text-2xl font-bold">Session Setup</h2>
      {experimentRunId && (
        <div className="glass p-3 text-sm text-accent-glow">
          This session will be linked to experiment run <span className="font-mono">{experimentRunId}</span>.
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2">
      <div>
        <label className="block text-sm text-foreground/60 mb-1">Display Name (optional)</label>
        <input
          className="w-full px-3 py-2 rounded-lg bg-surface border border-surface-border text-foreground focus:border-accent outline-none"
          placeholder="Anonymous"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
      </div>
      <div className="rounded-lg border border-surface-border bg-surface/40 p-3">
        <div className="text-sm font-medium">Local profile</div>
        <p className="mt-1 text-xs text-foreground/50">
          {profile ? `Continuing as ${profile.display_name}` : "Anonymous unless you create a local profile."}
        </p>
        {!profile && (
          <Button size="sm" variant="secondary" className="mt-3" onClick={createProfile} disabled={profileLoading}>
            {profileLoading ? "Creating..." : "Create Local Profile"}
          </Button>
        )}
      </div>
      </div>

      <div>
        <label className="block text-sm text-foreground/60 mb-2">Task</label>
        <div className="space-y-2">
          {TASKS.map((t) => (
            <label
              key={t.id}
              className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${taskId === t.id ? "border-accent bg-accent/5" : "border-surface-border hover:bg-surface"}`}
            >
              <input type="radio" name="task" checked={taskId === t.id} onChange={() => setTaskId(t.id)} className="mt-1 accent-accent" />
              <div>
                <div className="font-medium text-sm">{t.name}</div>
                <div className="text-xs text-foreground/50">{t.desc}</div>
              </div>
            </label>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-sm text-foreground/60 mb-2">Mode</label>
        <div className="flex gap-3">
          {MODES.map((m) => (
            <button
              key={m.id}
              onClick={() => setMode(m.id)}
              className={`px-4 py-2 rounded-lg text-sm transition-colors ${mode === m.id ? "bg-accent text-white" : "border border-surface-border text-foreground/70 hover:bg-surface"}`}
            >
              {m.name}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-sm text-foreground/60 mb-2">Signal Provider</label>
        <div className="grid gap-2 md:grid-cols-2">
          {providers.map((provider) => {
            const available = provider.health?.available !== false;
            return (
              <label
                key={provider.provider_id}
                className={`rounded-lg border p-3 text-sm transition-colors ${signalProviderId === provider.provider_id ? "border-accent bg-accent/5" : "border-surface-border bg-surface/30"} ${available ? "cursor-pointer" : "opacity-55"}`}
              >
                <div className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="provider"
                    disabled={!available || provider.provider_type === "replay"}
                    checked={signalProviderId === provider.provider_id}
                    onChange={() => setSignalProviderId(provider.provider_id)}
                    className="accent-accent"
                  />
                  <span className="font-medium">{provider.provider_id}</span>
                </div>
                <div className="mt-1 text-xs text-foreground/50">{provider.description}</div>
                <div className="mt-2 text-[11px] uppercase tracking-[0.14em] text-foreground/38">
                  {provider.provider_type} | {provider.health?.status || "unknown"}
                </div>
              </label>
            );
          })}
        </div>
      </div>

      {signalProviderId.includes("simulated") && (
        <div>
          <label className="block text-sm text-foreground/60 mb-2">Simulated Scenario</label>
          <select
            value={scenario}
            onChange={(e) => setScenario(e.target.value)}
            className="w-full rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm outline-none focus:border-accent"
          >
            {SCENARIOS.map((item) => (
              <option key={item.id} value={item.id}>{item.name}</option>
            ))}
          </select>
        </div>
      )}

      <DisclaimerBox />

      <label className="flex items-center gap-2 cursor-pointer">
        <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} className="accent-accent" />
        <span className="text-sm text-foreground/70">
          I understand this is a research prototype and not a medical device.
        </span>
      </label>

      <Button
        disabled={!consent}
        onClick={() => onStart({
          displayName: name || profile?.display_name || "Anonymous",
          taskId,
          mode,
          userId: profile?.user_id || window.localStorage.getItem("imagina_user_id"),
          signalProviderId,
          scenario,
          experimentRunId,
        })}
        size="lg"
        className="w-full"
      >
        Begin Session
      </Button>
    </div>
  );
}
