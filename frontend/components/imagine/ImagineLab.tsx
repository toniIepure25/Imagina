"use client";

import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import AnimusShell from "@/components/animus/AnimusShell";
import EvidenceMark from "@/components/evidence/EvidenceMark";
import { buttonStyles } from "@/components/common/Button";
import HudLabel from "@/components/system/HudLabel";
import AdaptiveTrace, { type AdaptiveSample } from "@/components/imagine/AdaptiveTrace";
import ConsentDialog from "@/components/imagine/ConsentDialog";
import DiffusionLane from "@/components/imagine/DiffusionLane";
import ImagineStage from "@/components/imagine/ImagineStage";
import ProvenanceLens from "@/components/imagine/ProvenanceLens";
import SignalConstellation from "@/components/imagine/SignalConstellation";
import WorldStrip from "@/components/imagine/WorldStrip";
import { downloadText } from "@/lib/preregistration";
import {
  ADAPTIVE_TARGETS,
  BAND_CHANNELS,
  DEFAULT_BRIEF,
  DEFAULT_SIGNALS,
  PHYSIOLOGY_CHANNELS,
  PRIMARY_CHANNELS,
  buildImagineScene,
  promptFingerprint,
  signalCoherence,
  styleLabel,
  type AdaptiveTarget,
  type ImagineBandId,
  type ImagineBrief,
  type ImagineChannelId,
  type ImaginePhysiologyId,
  type ImagineSignals,
  type ImagineStyle,
} from "@/lib/imagineScene";
import { buildConditioning, deriveControls } from "@/lib/imagine/conditioning";
import { createJob, getCapabilities, getJob, cancelJob, ImagineApiError } from "@/lib/imagine/client";
import { manifestAssetUrl, validateManifest } from "@/lib/imagine/manifest";
import { DEFAULT_POLICY, DEFAULT_POLICY_MEMORY, stepAdaptivePolicy, type PolicyMemory } from "@/lib/imagine/policy";
import { buildDiffusionRequestV2 } from "@/lib/imagine/request";
import { IMAGINE_PRESETS, presetById, type ImaginePreset } from "@/lib/imagine/presets";
import type { WorldSpec } from "@/lib/imagine/world";
import {
  SCENARIOS,
  SCENARIO_DURATION_SECONDS,
  scenarioAt,
  type ImagineScenarioId,
} from "@/lib/imagine/scenarios";
import type { ImagineCapabilities, ImagineJob } from "@/lib/imagine/types";

const STYLE_OPTIONS: ImagineStyle[] = ["dream", "cinematic", "gothic", "surreal", "minimal"];

const PROMPT_CHIPS = [
  "A quiet bioluminescent corridor under a violet sky, with a distant door and a still pool of water.",
  "A gothic library at blue hour, with a single lit portal between tall shelves.",
  "An ocean gate under a warm dusk sky, with slow drifting embers.",
  "A minimal white room with one door, one tree, and a soft cyan horizon.",
];

const SIGNAL_COPY: Record<ImagineChannelId, string> = {
  attention: "how much fine structure is held",
  arousal: "how much motion and shimmer is allowed",
  valence: "whether the palette runs warm or cool",
  vividness: "how dense and emissive the corridor becomes",
  fatigue: "how much fog softens the far end",
  confidence: "how stable the preview is between passes",
};

const TABS = ["Signals", "Adaptive", "Diffusion", "Provenance"] as const;
type Tab = (typeof TABS)[number];

function clampPercent(value: number): number {
  return Math.round(Math.max(0, Math.min(1, value)) * 100);
}

function SignalSlider({
  id,
  label,
  hint,
  effect,
  value,
  onChange,
}: {
  id: string;
  label: string;
  hint: string;
  effect: string;
  value: number;
  onChange: (value: number) => void;
}) {
  return (
    <div>
      <div className="flex items-baseline justify-between gap-2">
        <label htmlFor={`signal-${id}`} className="text-xs font-medium text-foreground/75">
          {label}
        </label>
        <span className="font-mono text-[11px] tabular-nums text-signal/80">{clampPercent(value)}</span>
      </div>
      <input
        id={`signal-${id}`}
        type="range"
        min={0}
        max={1}
        step={0.01}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        aria-valuetext={`${label}: ${clampPercent(value)} percent. ${SIGNAL_COPY[id as ImagineChannelId] ?? effect}`}
        className="mt-1 h-11 w-full cursor-pointer accent-[#6fe3c4]"
      />
      <div className="-mt-1 flex items-center justify-between gap-2 font-mono text-[11px] text-foreground/30">
        <span>{hint}</span>
        <span className="truncate text-right">{effect}</span>
      </div>
    </div>
  );
}

function TabButton({
  active,
  children,
  onClick,
}: {
  active: boolean;
  children: ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      onClick={onClick}
      className={`min-h-11 flex-1 border-b px-2 font-mono text-[10px] uppercase tracking-[0.12em] transition-colors ${
        active
          ? "border-lumen-mint/70 text-lumen-mint"
          : "border-transparent text-foreground/35 hover:text-foreground/70"
      }`}
    >
      {children}
    </button>
  );
}

export default function ImagineLab() {
  const [draftPrompt, setDraftPrompt] = useState(DEFAULT_BRIEF.prompt);
  const [brief, setBrief] = useState<ImagineBrief>(DEFAULT_BRIEF);
  const [negativePrompt, setNegativePrompt] = useState("people, faces, text, watermark");
  const [signals, setSignals] = useState<ImagineSignals>(DEFAULT_SIGNALS);
  const [style, setStyle] = useState<ImagineStyle>(DEFAULT_BRIEF.style);
  const [seed, setSeed] = useState(DEFAULT_BRIEF.seed);
  const [targetId, setTargetId] = useState<AdaptiveTarget["id"]>("immersion");
  const [adaptive, setAdaptive] = useState(false);
  const [firstPerson, setFirstPerson] = useState(true);
  const [advanced, setAdvanced] = useState(false);
  const [tab, setTab] = useState<Tab>("Signals");
  const [notice, setNotice] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);
  const [history, setHistory] = useState<ImagineSignals[]>([]);
  const [samples, setSamples] = useState<AdaptiveSample[]>([]);
  const [decision, setDecision] = useState({ reason: "Manual control. The policy is idle.", safetyStop: null as null | "fatigue" | "quality" });
  const [scenarioId, setScenarioId] = useState<ImagineScenarioId | null>(null);
  const [scenarioElapsed, setScenarioElapsed] = useState(0);
  const [scenarioSpeed, setScenarioSpeed] = useState(1);
  const [capabilities, setCapabilities] = useState<ImagineCapabilities | null>(null);
  const [capabilityError, setCapabilityError] = useState<string | null>(null);
  const [job, setJob] = useState<ImagineJob | null>(null);
  const [jobError, setJobError] = useState<string | null>(null);
  const [busyJob, setBusyJob] = useState(false);
  const [consentOpen, setConsentOpen] = useState(false);
  const [consentGiven, setConsentGiven] = useState(false);
  const [usingSkybox, setUsingSkybox] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [presetId, setPresetId] = useState<string | null>(null);
  const [instrumentOpen, setInstrumentOpen] = useState(false);
  const presetApplied = useRef(false);

  const stageRef = useRef<HTMLDivElement>(null);
  const movementRef = useRef({ x: 0, y: 0 });
  const signalsRef = useRef<ImagineSignals>(DEFAULT_SIGNALS);
  const historyRef = useRef<ImagineSignals[]>([]);
  const policyMemory = useRef<PolicyMemory>({ ...DEFAULT_POLICY_MEMORY });
  const policyLock = useRef(false);

  const target = ADAPTIVE_TARGETS.find((item) => item.id === targetId) ?? ADAPTIVE_TARGETS[1];
  const scene = useMemo(() => buildImagineScene(brief, signals), [brief, signals]);
  const world = scene.metadata.world as WorldSpec | undefined;
  const conditioning = useMemo(() => buildConditioning(signals, history, scenarioId ? "scenario" : "demo"), [history, scenarioId, signals]);
  const controls = useMemo(() => deriveControls(conditioning), [conditioning]);
  const coherence = signalCoherence(signals, target);
  const fingerprint = promptFingerprint(brief, signals).toString(16).padStart(8, "0");
  const manifestResult = useMemo(
    () => (job?.manifest ? validateManifest(job.manifest) : null),
    [job],
  );
  const activeManifest = manifestResult?.ok ? manifestResult.manifest : null;
  const environmentTextureUrl = usingSkybox && activeManifest ? manifestAssetUrl(activeManifest.skybox) : null;

  useEffect(() => {
    signalsRef.current = signals;
  }, [signals]);

  useEffect(() => {
    historyRef.current = history;
  }, [history]);

  useEffect(() => {
    const controller = new AbortController();
    void getCapabilities()
      .then((result) => {
        if (!controller.signal.aborted) setCapabilities(result);
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setCapabilities(null);
          setCapabilityError("Local API unreachable. The procedural stage still works; diffusion stays offline.");
        }
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!adaptive || scenarioId) return;
    const timer = window.setInterval(() => {
      if (policyLock.current) return;
      policyLock.current = true;
      const current = signalsRef.current;
      const currentHistory = historyRef.current;
      const result = stepAdaptivePolicy(
        current,
        target,
        buildConditioning(current, currentHistory),
        Date.now(),
        policyMemory.current,
        DEFAULT_POLICY,
        1000,
      );
      policyMemory.current = result.memory;
      setSignals(result.signals);
      setDecision({ reason: result.reason, safetyStop: result.safetyStop });
      setSamples((previous) => [
        ...previous.slice(-119),
        {
          at: Date.now(),
          attention: result.signals.attention,
          valence: result.signals.valence,
          intervention: result.intervention,
          safetyStop: result.safetyStop,
        },
      ]);
      setHistory((previous) => [...previous.slice(-29), result.signals]);
      policyLock.current = false;
    }, 1000);
    return () => window.clearInterval(timer);
  }, [adaptive, scenarioId, target]);

  useEffect(() => {
    if (!scenarioId) return;
    const timer = window.setInterval(() => {
      setScenarioElapsed((previous) => {
        const next = Math.min(SCENARIO_DURATION_SECONDS, previous + 0.2 * scenarioSpeed);
        const frame = scenarioAt(scenarioId, next);
        const stop = frame.fatigue >= DEFAULT_POLICY.fatigueStop ? "fatigue" : frame.signal_quality < DEFAULT_POLICY.qualityHold ? "quality" : null;
        setSignals(frame);
        setDecision({
          reason: `Simulated ${scenarioId} scenario at ${next.toFixed(0)} s. ${stop ? "Safety hold is active." : "No live person is involved."}`,
          safetyStop: stop,
        });
        setSamples((previous) => [
          ...previous.slice(-119),
          {
            at: Date.now(),
            attention: frame.attention,
            valence: frame.valence,
            intervention: false,
            safetyStop: stop,
          },
        ]);
        if (next >= SCENARIO_DURATION_SECONDS) {
          setScenarioId(null);
          setAdaptive(false);
        }
        return next;
      });
    }, 200);
    return () => window.clearInterval(timer);
  }, [scenarioId, scenarioSpeed]);

  useEffect(() => {
    if (!notice) return;
    const timeout = window.setTimeout(() => setNotice(null), 3200);
    return () => window.clearTimeout(timeout);
  }, [notice]);

  useEffect(() => {
    if (!job || job.state === "succeeded" || job.state === "failed" || job.state === "cancelled") return;
    let active = true;
    const timer = window.setInterval(() => {
      void getJob(job.id)
        .then((next) => {
          if (active) setJob(next);
        })
        .catch((error: unknown) => {
          if (active) setJobError(error instanceof Error ? error.message : "Could not refresh the job.");
        });
    }, 1500);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [job]);

  useEffect(() => {
    const onChange = () => setIsFullscreen(Boolean(document.fullscreenElement));
    document.addEventListener("fullscreenchange", onChange);
    return () => document.removeEventListener("fullscreenchange", onChange);
  }, []);

  useEffect(() => {
    if (presetApplied.current) return;
    presetApplied.current = true;
    const timer = window.setTimeout(() => {
      const id = new URLSearchParams(window.location.search).get("preset");
      if (!id) return;
      const preset = presetById(id);
      if (!preset) {
        setNotice("That world preset was not found. The current world is unchanged.");
        return;
      }
      setPresetId(preset.id);
      setDraftPrompt(preset.prompt);
      setStyle(preset.style);
      setSeed(preset.seed);
      setBrief({ prompt: preset.prompt, style: preset.style, seed: preset.seed, title: preset.title });
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  const applyPreset = (preset: ImaginePreset) => {
    setPresetId(preset.id);
    setDraftPrompt(preset.prompt);
    setStyle(preset.style);
    setSeed(preset.seed);
    setBrief({ prompt: preset.prompt, style: preset.style, seed: preset.seed, title: preset.title });
    setAdaptive(false);
    setScenarioId(null);
    window.history.replaceState({}, "", `${window.location.pathname}?preset=${preset.id}`);
    setNotice(`${preset.title} loaded. Built locally, frame by frame.`);
  };

  const applyBrief = () => {
    const prompt = draftPrompt.trim() || DEFAULT_BRIEF.prompt;
    setDraftPrompt(prompt);
    setBrief({ prompt, style, seed: seed.trim() || DEFAULT_BRIEF.seed, title: undefined });
    setPresetId(null);
    window.history.replaceState({}, "", window.location.pathname);
    setNotice("Local preview rebuilt. No model was called.");
  };

  const applyChip = (prompt: string) => {
    setDraftPrompt(prompt);
    setBrief({ prompt, style, seed: seed.trim() || DEFAULT_BRIEF.seed, title: undefined });
    setPresetId(null);
    window.history.replaceState({}, "", window.location.pathname);
  };

  const resample = () => {
    const next = `imagina-${revision + 1}`;
    setRevision((value) => value + 1);
    setSeed(next);
    setBrief((current) => ({ ...current, seed: next, title: undefined }));
    setPresetId(null);
    window.history.replaceState({}, "", window.location.pathname);
    setNotice("Resampled the local scene. Diffusion remains disconnected.");
  };

  const updateSignal = (id: keyof ImagineSignals, value: number) => {
    setAdaptive(false);
    setScenarioId(null);
    setSignals((current) => ({ ...current, [id]: value }));
    policyMemory.current = { ...DEFAULT_POLICY_MEMORY };
  };

  const payload = useMemo(
    () =>
      buildDiffusionRequestV2({
        brief,
        negativePrompt,
        conditioning,
        controls,
        scene,
        target: targetId,
        signals,
      }),
    [brief, conditioning, controls, negativePrompt, scene, signals, targetId],
  );

  const downloadJob = () => {
    downloadText("imagina-diffusion-request-v2.json", JSON.stringify(payload, null, 2), "application/json");
    setNotice("Downloaded the v2 request contract. Nothing was executed.");
  };

  const submitJob = async () => {
    if (!capabilities || capabilities.diffusion.status === "blocked") {
      setJobError("Diffusion is offline. The local procedural stage remains active.");
      return;
    }
    setBusyJob(true);
    setJobError(null);
    setUsingSkybox(false);
    try {
      const created = await createJob(payload);
      setJob(created);
      setTab("Diffusion");
      setNotice("Request accepted by the configured worker.");
    } catch (error) {
      if (error instanceof ImagineApiError) {
        setJobError(`${error.code}: ${error.message}`);
      } else {
        setJobError(error instanceof Error ? error.message : "The request failed.");
      }
    } finally {
      setBusyJob(false);
    }
  };

  const requestSkybox = () => {
    if (!capabilities || capabilities.diffusion.status === "blocked") {
      setJobError("Diffusion is offline. No request was sent.");
      return;
    }
    if (!consentGiven) {
      setConsentOpen(true);
      return;
    }
    void submitJob();
  };

  const handleConsent = () => {
    setConsentOpen(false);
    setConsentGiven(true);
    void submitJob();
  };

  const handleCancel = async () => {
    if (!job) return;
    setBusyJob(true);
    try {
      const next = await cancelJob(job.id);
      setJob(next);
      setNotice("Job cancelled. The local scene is unchanged.");
    } catch (error) {
      setJobError(error instanceof Error ? error.message : "Cancellation failed.");
    } finally {
      setBusyJob(false);
    }
  };

  const toggleFullscreen = async () => {
    if (document.fullscreenElement) {
      await document.exitFullscreen();
      return;
    }
    await stageRef.current?.requestFullscreen?.();
  };

  const captureStill = () => {
    const canvas = stageRef.current?.querySelector("canvas");
    if (!canvas) {
      setNotice("The stage is still loading.");
      return;
    }
    const anchor = document.createElement("a");
    anchor.href = canvas.toDataURL("image/png");
    anchor.download = "imagine-still.png";
    anchor.click();
    setNotice("Captured the local stage. Nothing was uploaded.");
  };

  const startScenario = (id: ImagineScenarioId) => {
    setScenarioId(id);
    setScenarioElapsed(0);
    setAdaptive(false);
    setSamples([]);
    setSignals(scenarioAt(id, 0));
  };

  const effectiveSamples = samples;
  const quality = conditioning.vector.signal_quality;

  return (
    <AnimusShell active="imagine" workspace>
      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto bg-[#05070e] xl:h-full xl:overflow-hidden">
        <header className="sticky top-0 z-30 flex min-h-[68px] shrink-0 items-center justify-between gap-3 border-b border-white/[0.06] bg-[#05070e]/94 px-3 backdrop-blur-xl sm:px-5">
          <div className="flex min-w-0 items-center gap-4">
            <div className="hidden h-9 w-9 shrink-0 place-items-center rounded-full border border-lumen-mint/25 sm:grid">
              <span className="h-1.5 w-1.5 rounded-full bg-lumen-mint shadow-[0_0_12px_rgba(136,240,214,0.9)]" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <HudLabel className="text-lumen-mint/70">LUMEN / IMAGINE</HudLabel>
                <span className="hidden font-mono text-[9px] uppercase tracking-[0.16em] text-foreground/25 md:inline">
                  first-person world engine
                </span>
              </div>
              <h1 className="truncate font-display text-[21px] leading-tight tracking-[-0.01em] text-lumen-bone sm:text-[25px]">
                Describe a place. Step inside it.
              </h1>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-1.5">
            <span className="hidden items-center gap-1.5 border border-lumen-mint/20 bg-lumen-mint/[0.04] px-2 py-1 font-mono text-[9px] uppercase tracking-[0.14em] text-lumen-mint/70 lg:inline-flex">
              <span className="h-1 w-1 rounded-full bg-lumen-mint" />
              procedural
            </span>
            <span className="hidden items-center gap-1.5 border border-lumen-ember/20 bg-lumen-ember/[0.03] px-2 py-1 font-mono text-[9px] uppercase tracking-[0.14em] text-lumen-ember/65 md:inline-flex">
              diffusion lane closed
            </span>
            <button
              type="button"
              onClick={() => setInstrumentOpen(true)}
              aria-expanded={instrumentOpen}
              className="min-h-10 border border-white/10 px-2.5 font-mono text-[10px] uppercase tracking-[0.12em] text-foreground/50 transition-colors hover:border-lumen-mint/30 hover:text-lumen-mint xl:hidden"
            >
              Instrument
            </button>
            <button
              type="button"
              onClick={captureStill}
              className="min-h-10 px-2 font-mono text-[10px] uppercase tracking-[0.12em] text-foreground/35 transition-colors hover:text-foreground/75"
            >
              Capture
            </button>
            <button
              type="button"
              onClick={() => void toggleFullscreen()}
              aria-label={isFullscreen ? "Exit fullscreen" : "Enter fullscreen"}
              className="min-h-10 border border-white/10 px-2.5 font-mono text-[10px] uppercase tracking-[0.12em] text-foreground/45 transition-colors hover:border-white/25"
            >
              {isFullscreen ? "Exit" : "Full"}
            </button>
            <EvidenceMark evidenceId="imagine.scene" />
          </div>
        </header>

        <div className="flex min-h-0 flex-1 flex-col xl:grid xl:grid-cols-[322px_minmax(0,1fr)_372px] xl:grid-rows-[minmax(0,1fr)] xl:overflow-hidden">
          <aside className="order-2 min-h-0 overflow-y-auto border-t border-white/[0.06] bg-[#060810]/92 p-3.5 xl:order-1 xl:border-r xl:border-t-0">
            <WorldStrip
              presets={IMAGINE_PRESETS}
              activeId={presetId}
              onSelect={applyPreset}
              onResample={resample}
            />
            <div className="mt-4 flex items-start justify-between gap-2">
              <div>
                <HudLabel>Composer</HudLabel>
                <h2 className="mt-1 font-display text-[22px] leading-tight tracking-[-0.01em] text-lumen-bone">
                  Direct the world.
                </h2>
              </div>
              <span className="mt-1 border border-white/10 px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-[0.14em] text-foreground/30">
                v2
              </span>
            </div>
            <p className="mt-2 text-[11px] leading-5 text-foreground/40">
              Language owns the scene. The signal vector tunes light, haze, and pace. Every preview is composed in this
              browser; the diffusion lane stays closed until a worker is attached.
            </p>

            {world ? (
              <div className="mt-3 grid grid-cols-3 gap-px border border-white/[0.07] bg-white/[0.06]">
                {[
                  ["biome", world.biome],
                  ["form", world.archetype],
                  ["light", world.timeOfDay],
                ].map(([label, value]) => (
                  <div key={label} className="bg-[#080b13] px-2 py-1.5">
                    <p className="font-mono text-[8px] uppercase tracking-[0.16em] text-foreground/25">{label}</p>
                    <p className="mt-0.5 truncate text-[10px] capitalize text-foreground/65">{value}</p>
                  </div>
                ))}
              </div>
            ) : null}

            <form
              className="mt-4 space-y-3"
              onSubmit={(event) => {
                event.preventDefault();
                applyBrief();
              }}
            >
              <div>
                <div className="flex items-baseline justify-between gap-2">
                  <label htmlFor="imagine-prompt" className="font-mono text-[11px] uppercase tracking-[0.16em] text-foreground/45">
                    Initial description
                  </label>
                  <span className="font-mono text-[11px] text-foreground/25">{draftPrompt.length}/420</span>
                </div>
                <textarea
                  id="imagine-prompt"
                  value={draftPrompt}
                  maxLength={420}
                  rows={6}
                  onChange={(event) => setDraftPrompt(event.target.value)}
                  className="mt-2 w-full resize-y rounded-xl border border-white/10 bg-white/[0.025] px-3 py-2.5 text-xs leading-5 text-foreground/85 outline-none transition-colors placeholder:text-foreground/25 focus:border-signal/45"
                  placeholder="A corridor, a threshold, a light you can almost name…"
                />
                <p className="mt-1.5 text-[11px] leading-5 text-foreground/30">
                  A brief, not a diagnosis. Text stays in this browser.
                </p>
              </div>

              <div className="flex flex-wrap gap-1.5">
                {PROMPT_CHIPS.map((chip) => (
                  <button
                    key={chip}
                    type="button"
                    onClick={() => applyChip(chip)}
                    className="min-h-9 rounded-full border border-white/10 px-2.5 py-1 text-left text-[11px] text-foreground/45 transition-colors hover:border-signal/30 hover:text-foreground/75"
                  >
                    {chip.split(",")[0]}
                  </button>
                ))}
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label htmlFor="imagine-style" className="font-mono text-[11px] uppercase tracking-[0.16em] text-foreground/45">
                    Style
                  </label>
                  <select
                    id="imagine-style"
                    value={style}
                    onChange={(event) => {
                      const next = event.target.value as ImagineStyle;
                      setStyle(next);
                      setBrief((current) => ({ ...current, style: next, title: undefined }));
                      setPresetId(null);
                    }}
                    className="mt-1.5 h-11 w-full rounded-lg border border-white/10 bg-[#0a0d17] px-2 text-xs text-foreground/75 outline-none focus:border-signal/45"
                  >
                    {STYLE_OPTIONS.map((option) => (
                      <option key={option} value={option}>
                        {styleLabel(option)}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label htmlFor="imagine-seed" className="font-mono text-[11px] uppercase tracking-[0.16em] text-foreground/45">
                    Seed
                  </label>
                  <input
                    id="imagine-seed"
                    value={seed}
                    maxLength={40}
                    onChange={(event) => {
                      setSeed(event.target.value);
                      setPresetId(null);
                      setBrief((current) => ({ ...current, seed: event.target.value, title: undefined }));
                    }}
                    className="mt-1.5 h-11 w-full rounded-lg border border-white/10 bg-white/[0.025] px-2 font-mono text-[11px] text-foreground/70 outline-none focus:border-signal/45"
                  />
                </div>
              </div>

              <details className="rounded-lg border border-white/[0.07] bg-white/[0.015] px-2.5 py-2">
                <summary className="cursor-pointer font-mono text-[11px] uppercase tracking-[0.12em] text-foreground/35">
                  Negative prompt
                </summary>
                <textarea
                  value={negativePrompt}
                  maxLength={240}
                  rows={2}
                  onChange={(event) => setNegativePrompt(event.target.value)}
                  className="mt-2 w-full resize-y rounded-lg border border-white/10 bg-white/[0.02] px-2 py-1.5 text-[11px] text-foreground/65 outline-none focus:border-signal/40"
                />
              </details>

              <div className="flex gap-2">
                <button
                  type="submit"
                  className={buttonStyles({
                    variant: "primary",
                    size: "sm",
                    className: "min-h-11 flex-1 font-mono text-[11px] uppercase tracking-[0.12em]",
                  })}
                >
                  Build preview
                </button>
                <button
                  type="button"
                  onClick={resample}
                  className={buttonStyles({
                    variant: "secondary",
                    size: "sm",
                    className: "min-h-11 font-mono text-[11px] uppercase tracking-[0.12em]",
                  })}
                >
                  Resample
                </button>
              </div>
              <p className="font-mono text-[11px] text-foreground/25">
                scene hash {fingerprint} · {scene.entities.length} elements · local only
              </p>
            </form>

            <div className="mt-4 rounded-xl border border-white/[0.07] bg-white/[0.02] p-3">
              <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-foreground/35">Pipeline</p>
              <ol className="mt-2 space-y-1.5 font-mono text-[11px]">
                <li className="flex justify-between gap-2">
                  <span className="text-foreground/45">text brief</span>
                  <span className="text-signal/75">ready</span>
                </li>
                <li className="flex justify-between gap-2">
                  <span className="text-foreground/45">16D conditioning</span>
                  <span className="text-signal/75">ready</span>
                </li>
                <li className="flex justify-between gap-2">
                  <span className="text-foreground/45">local first-person</span>
                  <span className="text-accent-glow/75">active</span>
                </li>
                <li className="flex justify-between gap-2">
                  <span className="text-foreground/45">A100 skybox</span>
                  <span className="text-lock/80">blocked</span>
                </li>
              </ol>
              <button
                type="button"
                onClick={downloadJob}
                className="mt-3 inline-flex min-h-11 w-full items-center justify-center rounded-lg border border-white/10 px-3 font-mono text-[11px] uppercase tracking-[0.1em] text-foreground/45 hover:border-white/25"
              >
                Download job spec
              </button>
            </div>

            <p className="mt-4 border-t border-white/[0.07] pt-3 text-[11px] leading-5 text-foreground/30">
              Symbolic scene instrument. No thought decoding, dream decoding, imagery reconstruction, diagnosis, or
              validated imagery score. Claim ceiling L1 behavioural-assisted.
            </p>
          </aside>

          <section
            className="relative order-1 flex min-h-[64vh] min-w-0 flex-col border-b border-white/[0.06] xl:order-2 xl:h-full xl:min-h-0 xl:border-b-0"
            ref={stageRef}
          >
            <div className="min-h-0 flex-1">
              <ImagineStage
                scene={scene}
                firstPerson={firstPerson}
                style={style}
                signals={signals}
                onToggleFirstPerson={() => setFirstPerson((value) => !value)}
                environmentTextureUrl={environmentTextureUrl}
                movementRef={movementRef}
                diffusionState={usingSkybox ? "generated" : "offline"}
              />
            </div>
            <div className="grid grid-cols-2 gap-px border-t border-white/[0.06] bg-white/[0.05] sm:grid-cols-4">
              {[
                ["engine", usingSkybox ? "hybrid skybox" : "lumen procedural"],
                ["view", firstPerson ? "first person" : "orbit"],
                ["adaptive", scenarioId ? `${scenarioId} scenario` : adaptive ? `${target.label} loop` : "manual"],
                ["coherence", `${clampPercent(coherence)}%`],
              ].map(([label, value]) => (
                <div key={label} className="bg-[#060810] px-3 py-2.5">
                  <p className="font-mono text-[8px] uppercase tracking-[0.18em] text-foreground/25">{label}</p>
                  <p className="mt-0.5 truncate text-[11px] text-foreground/70">{value}</p>
                </div>
              ))}
            </div>
            <button
              type="button"
              onClick={() => setInstrumentOpen(true)}
              className="absolute bottom-[70px] right-3 z-20 min-h-10 border border-lumen-mint/25 bg-[#07120f]/85 px-3 font-mono text-[10px] uppercase tracking-[0.14em] text-lumen-mint/80 backdrop-blur xl:hidden"
            >
              Signals
            </button>
          </section>

          <aside
            className={`${
              instrumentOpen ? "fixed inset-x-0 bottom-0 top-[68px] z-40 block" : "hidden"
            } min-h-0 overflow-y-auto border-t border-white/[0.06] bg-[#060810] p-4 xl:static xl:order-3 xl:block xl:border-l xl:border-t-0`}
          >
            <div className="flex items-center justify-between gap-2">
              <div>
                <HudLabel>Instrument</HudLabel>
                <h2 className="mt-1 font-display text-lg leading-tight text-lumen-bone">Signals, state, provenance</h2>
              </div>
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => {
                    setSignals(DEFAULT_SIGNALS);
                    setAdaptive(false);
                    setScenarioId(null);
                    setSamples([]);
                    setHistory([]);
                    policyMemory.current = { ...DEFAULT_POLICY_MEMORY };
                    setNotice("Signal vector reset to the demo defaults.");
                  }}
                  className="min-h-10 px-2 font-mono text-[10px] uppercase tracking-[0.1em] text-foreground/35 hover:text-foreground/70"
                >
                  Reset
                </button>
                <button
                  type="button"
                  onClick={() => setInstrumentOpen(false)}
                  className="min-h-10 border border-white/10 px-2 font-mono text-[10px] uppercase tracking-[0.1em] text-foreground/40 xl:hidden"
                >
                  Close
                </button>
              </div>
            </div>

            <div
              role="tablist"
              aria-label="Imagine instrument panels"
              className="mt-3 flex gap-1 border-b border-white/[0.07]"
            >
              {TABS.map((item) => (
                <TabButton key={item} active={tab === item} onClick={() => setTab(item)}>
                  {item}
                </TabButton>
              ))}
            </div>

            {tab === "Signals" ? (
              <div role="tabpanel" aria-label="Signals" className="mt-3 space-y-3">
                <div className="rounded-lg border border-lock/15 bg-lock/[0.03] px-2.5 py-2 text-[11px] leading-5 text-foreground/40">
                  Demo control surface, not a measurement. No EEG, HRV, or EDA device is connected.
                </div>
                <SignalConstellation conditioning={conditioning} />
                <div className="space-y-4">
                  {PRIMARY_CHANNELS.map((channel) => (
                    <SignalSlider
                      key={channel.id}
                      id={channel.id}
                      label={channel.label}
                      hint={channel.hint}
                      effect={channel.sceneEffect}
                      value={signals[channel.id]}
                      onChange={(value) => updateSignal(channel.id, value)}
                    />
                  ))}
                </div>
                <div>
                  <SignalSlider
                    id="signal_quality"
                    label="Demo signal quality"
                    hint="gates how much influence the vector has"
                    effect="quality gate"
                    value={quality}
                    onChange={(value) => updateSignal("signal_quality", value)}
                  />
                </div>
                <button
                  type="button"
                  aria-expanded={advanced}
                  onClick={() => setAdvanced((value) => !value)}
                  className="flex min-h-11 w-full items-center justify-between rounded-lg border border-white/10 px-2.5 text-left font-mono text-[11px] uppercase tracking-[0.14em] text-foreground/45 hover:border-white/20 hover:text-foreground/70"
                >
                  <span>Bands + physiology</span>
                  <span aria-hidden="true">{advanced ? "−" : "+"}</span>
                </button>
                {advanced ? (
                  <div className="space-y-4 rounded-xl border border-white/[0.07] bg-white/[0.02] p-3">
                    {BAND_CHANNELS.map((channel) => (
                      <SignalSlider
                        key={channel.id}
                        id={channel.id}
                        label={channel.label}
                        hint={channel.hint}
                        effect="band power"
                        value={signals[channel.id as ImagineBandId]}
                        onChange={(value) => updateSignal(channel.id as ImagineBandId, value)}
                      />
                    ))}
                    {PHYSIOLOGY_CHANNELS.map((channel) => (
                      <SignalSlider
                        key={channel.id}
                        id={channel.id}
                        label={channel.label}
                        hint={channel.hint}
                        effect="physiology"
                        value={signals[channel.id as ImaginePhysiologyId]}
                        onChange={(value) => updateSignal(channel.id as ImaginePhysiologyId, value)}
                      />
                    ))}
                  </div>
                ) : null}
              </div>
            ) : null}

            {tab === "Adaptive" ? (
              <div role="tabpanel" aria-label="Adaptive" className="mt-3 space-y-3">
                <div className="rounded-xl border border-signal/15 bg-signal/[0.025] p-3">
                  <div className="flex items-center justify-between gap-2">
                    <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-signal/70">Target</p>
                    <button
                      type="button"
                      role="switch"
                      aria-checked={adaptive}
                      onClick={() => {
                        setScenarioId(null);
                        setAdaptive((value) => !value);
                      }}
                      className={`min-h-9 rounded-full border px-2.5 font-mono text-[11px] uppercase tracking-[0.12em] transition-colors ${
                        adaptive
                          ? "border-signal/40 bg-signal/[0.1] text-signal"
                          : "border-white/10 text-foreground/40 hover:text-foreground/70"
                      }`}
                    >
                      {adaptive ? "loop on" : "loop off"}
                    </button>
                  </div>
                  <div className="mt-2 grid grid-cols-3 gap-1.5" role="group" aria-label="Adaptive target">
                    {ADAPTIVE_TARGETS.map((option) => (
                      <button
                        key={option.id}
                        type="button"
                        aria-pressed={targetId === option.id}
                        onClick={() => {
                          setTargetId(option.id);
                          setAdaptive(true);
                          setScenarioId(null);
                          policyMemory.current = { ...DEFAULT_POLICY_MEMORY };
                        }}
                        className={`min-h-10 rounded-lg border px-1 text-[11px] transition-colors ${
                          targetId === option.id
                            ? "border-signal/35 bg-signal/[0.08] text-signal"
                            : "border-white/10 text-foreground/40 hover:text-foreground/70"
                        }`}
                      >
                        {option.label}
                      </button>
                    ))}
                  </div>
                  <p className="mt-2 text-[11px] leading-5 text-foreground/40">{target.description}</p>
                  <div className="mt-2">
                    <div className="flex items-center justify-between font-mono text-[11px] text-foreground/35">
                      <span>coherence</span>
                      <span className="tabular-nums text-signal/75">{clampPercent(coherence)}%</span>
                    </div>
                    <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-white/10">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-signal/50 to-signal transition-[width] duration-500"
                        style={{ width: `${clampPercent(coherence)}%` }}
                      />
                    </div>
                  </div>
                  <p className="mt-2 text-[11px] leading-5 text-foreground/30">
                    Capped at 0.12/s with deadband, hysteresis, dwell, and a fatigue stop. Not live neurofeedback.
                  </p>
                  {decision.safetyStop ? (
                    <p role="alert" className="mt-2 rounded-lg border border-lock/25 bg-lock/[0.06] px-2 py-1.5 font-mono text-[11px] text-lock/80">
                      safety hold: {decision.safetyStop}
                    </p>
                  ) : null}
                </div>

                <AdaptiveTrace samples={effectiveSamples} target={target} reason={decision.reason} />

                <div className="rounded-xl border border-white/[0.07] bg-white/[0.02] p-3">
                  <div className="flex items-center justify-between gap-2">
                    <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-foreground/35">Simulated scenarios</p>
                    <button
                      type="button"
                      onClick={() => setScenarioSpeed((value) => (value === 1 ? 2 : 1))}
                      className="min-h-9 font-mono text-[11px] text-foreground/40 hover:text-foreground/70"
                    >
                      {scenarioSpeed}×
                    </button>
                  </div>
                  <div className="mt-2 grid grid-cols-2 gap-1.5">
                    {SCENARIOS.map((scenario) => (
                      <button
                        key={scenario.id}
                        type="button"
                        aria-pressed={scenarioId === scenario.id}
                        onClick={() => startScenario(scenario.id)}
                        className={`min-h-10 rounded-lg border px-2 text-left text-[11px] transition-colors ${
                          scenarioId === scenario.id
                            ? "border-signal/35 bg-signal/[0.08] text-signal"
                            : "border-white/10 text-foreground/45 hover:text-foreground/75"
                        }`}
                      >
                        {scenario.label}
                      </button>
                    ))}
                  </div>
                  <p className="mt-2 text-[11px] leading-5 text-foreground/30">
                    {scenarioId
                      ? `${scenarioId} at ${scenarioElapsed.toFixed(0)} s of ${SCENARIO_DURATION_SECONDS}. No live person is involved.`
                      : SCENARIOS.find((scenario) => scenario.id === scenarioId)?.description ??
                        "Synthetic traces only. They exercise the policy and safety holds without a device."}
                  </p>
                </div>
              </div>
            ) : null}

            {tab === "Diffusion" ? (
              <div role="tabpanel" aria-label="Diffusion" className="mt-3">
                <DiffusionLane
                  capabilities={capabilities}
                  job={job}
                  busy={busyJob}
                  error={jobError ?? capabilityError}
                  usingSkybox={usingSkybox}
                  onRequest={requestSkybox}
                  onCancel={() => void handleCancel()}
                  onToggleSkybox={() => {
                    if (!activeManifest) {
                      setNotice("No valid skybox manifest. Staying on the procedural sky.");
                      return;
                    }
                    setUsingSkybox((value) => !value);
                  }}
                  onDownload={downloadJob}
                />
              </div>
            ) : null}

            {tab === "Provenance" ? (
              <div role="tabpanel" aria-label="Provenance" className="mt-3">
                <ProvenanceLens
                  scene={scene}
                  conditioning={conditioning}
                  controls={controls}
                  manifest={activeManifest}
                />
              </div>
            ) : null}
          </aside>
        </div>

        {(notice || capabilityError) ? (
          <div
            role="status"
            aria-live="polite"
            className="pointer-events-none fixed bottom-4 left-1/2 z-[60] max-w-[92vw] -translate-x-1/2 rounded-full border border-signal/25 bg-[#081018]/95 px-3 py-2 text-center text-xs text-foreground/75 shadow-xl backdrop-blur"
          >
            {notice ?? capabilityError}
          </div>
        ) : null}

        <ConsentDialog
          open={consentOpen}
          prompt={brief.prompt}
          vectorHash={conditioning.vectorHash}
          onCancel={() => setConsentOpen(false)}
          onConfirm={handleConsent}
        />
      </div>
    </AnimusShell>
  );
}
