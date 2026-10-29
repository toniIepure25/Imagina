import type { SceneAttribute, SceneEntity, SceneGraph, Vec3 } from "@/lib/animusStudioApi";
import { fnv1a, mulberry32 } from "@/lib/randomization";
import { composeImagineWorld } from "./imagine/composeWorld";
import { deriveWorldSpec } from "./imagine/world";

export type ImagineStyle = "dream" | "cinematic" | "gothic" | "surreal" | "minimal";

export type ImagineChannelId =
  | "attention"
  | "arousal"
  | "valence"
  | "vividness"
  | "fatigue"
  | "confidence";

export type ImagineBandId = "theta" | "alpha" | "beta" | "gamma";
export type ImaginePhysiologyId = "hrv" | "eda";

export interface ImagineSignals extends Record<ImagineChannelId, number> {
  theta: number;
  alpha: number;
  beta: number;
  gamma: number;
  hrv: number;
  eda: number;
  signal_quality: number;
}

export interface ImagineBrief {
  prompt: string;
  style: ImagineStyle;
  seed: string;
  title?: string;
}

export interface AdaptiveTarget {
  id: "calm" | "immersion" | "exploration";
  label: string;
  description: string;
  target: Record<ImagineChannelId, number>;
}

export interface DiffusionJob {
  schema: "IMAGINA-DIFFUSION-JOB-v1";
  status: "blocked";
  engine: "latent-scene-diffusion";
  blocker: string;
  model: {
    slot: string;
    candidate: string;
    precision: string;
    minimumVramGb: number;
  };
  prompt: string;
  negativePrompt: string;
  conditioning: {
    text: boolean;
    depth: boolean;
    segmentation: boolean;
    signalVector: ImagineSignals;
    adaptiveTarget: AdaptiveTarget["id"] | null;
    firstPerson: boolean;
  };
  render: {
    width: number;
    height: number;
    steps: number;
    guidance: number;
    seed: number;
    fps: number;
  };
  output: {
    format: "scene_graph+preview";
    firstPerson: true;
    adaptationHz: number;
  };
  boundary: string;
}

export const DEFAULT_SIGNALS: ImagineSignals = {
  attention: 0.62,
  arousal: 0.44,
  valence: 0.68,
  vividness: 0.58,
  fatigue: 0.22,
  confidence: 0.54,
  theta: 0.48,
  alpha: 0.55,
  beta: 0.46,
  gamma: 0.38,
  hrv: 0.57,
  eda: 0.33,
  signal_quality: 0.86,
};

export const DEFAULT_BRIEF: ImagineBrief = {
  prompt:
    "A quiet bioluminescent corridor under a violet sky, with a distant door, drifting light, and a still pool of water.",
  style: "dream",
  seed: "imagina-first-person",
};

export const PRIMARY_CHANNELS: Array<{
  id: ImagineChannelId;
  label: string;
  hint: string;
  sceneEffect: string;
}> = [
  { id: "attention", label: "Attention", hint: "Focus stability", sceneEffect: "detail + element count" },
  { id: "arousal", label: "Arousal", hint: "Activation", sceneEffect: "motion + shimmer" },
  { id: "valence", label: "Valence", hint: "Affective tone", sceneEffect: "warm/cool palette" },
  { id: "vividness", label: "Vividness", hint: "Self-reported", sceneEffect: "density + emissive light" },
  { id: "fatigue", label: "Fatigue", hint: "Load", sceneEffect: "fog + reduced clarity" },
  { id: "confidence", label: "Confidence", hint: "Estimate quality", sceneEffect: "stability + star count" },
];

export const BAND_CHANNELS: Array<{ id: ImagineBandId; label: string; hint: string }> = [
  { id: "theta", label: "Theta", hint: "Drift / fog" },
  { id: "alpha", label: "Alpha", hint: "Calm glow" },
  { id: "beta", label: "Beta", hint: "Detail" },
  { id: "gamma", label: "Gamma", hint: "Shimmer" },
];

export const PHYSIOLOGY_CHANNELS: Array<{ id: ImaginePhysiologyId; label: string; hint: string }> = [
  { id: "hrv", label: "HRV", hint: "Motion smoothness" },
  { id: "eda", label: "EDA", hint: "Arousal coupling" },
];

export const ADAPTIVE_TARGETS: AdaptiveTarget[] = [
  {
    id: "calm",
    label: "Calm",
    description: "Lower fog and motion; hold attention. For down-regulation demos.",
    target: { attention: 0.72, arousal: 0.26, valence: 0.72, vividness: 0.54, fatigue: 0.16, confidence: 0.68 },
  },
  {
    id: "immersion",
    label: "Immersion",
    description: "Denser scene, more light and motion. For presence demos.",
    target: { attention: 0.8, arousal: 0.62, valence: 0.64, vividness: 0.8, fatigue: 0.3, confidence: 0.6 },
  },
  {
    id: "exploration",
    label: "Exploration",
    description: "Brighter, more varied palette and a wider corridor.",
    target: { attention: 0.6, arousal: 0.54, valence: 0.8, vividness: 0.78, fatigue: 0.24, confidence: 0.52 },
  },
];

const STYLE_LABELS: Record<ImagineStyle, string> = {
  dream: "Dream",
  cinematic: "Cinematic",
  gothic: "Gothic",
  surreal: "Surreal",
  minimal: "Minimal",
};

const STYLE_TUNING: Record<ImagineStyle, { fog: number; stars: number; aurora: boolean; key: number }> = {
  dream: { fog: 0.032, stars: 620, aurora: true, key: 1.15 },
  cinematic: { fog: 0.024, stars: 260, aurora: false, key: 1.25 },
  gothic: { fog: 0.058, stars: 300, aurora: false, key: 0.8 },
  surreal: { fog: 0.045, stars: 920, aurora: true, key: 1.4 },
  minimal: { fog: 0.012, stars: 120, aurora: false, key: 0.95 },
};

const KIND_HINTS: Array<[RegExp, string]> = [
  [/\bdoor\b|\bgate\b|\bthreshold\b/i, "door"],
  [/\bportal\b|\bgateway\b|\bpassage\b/i, "portal"],
  [/\bcrystal\b|\bprism\b|\bglass\b/i, "crystal"],
  [/\btree\b|\bforest\b|\bgrove\b|\bwood\b/i, "tree"],
  [/\bwater\b|\bpool\b|\blake\b|\bocean\b|\briver\b/i, "water"],
  [/\bmountain\b|\bpeak\b|\bridge\b/i, "mountain"],
  [/\bfire\b|\bflame\b|\bember\b/i, "fire"],
  [/\bcastle\b|\btower\b|\bhall\b/i, "castle"],
  [/\bperson\b|\bfigure\b|\bpresence\b|\bguardian\b/i, "person"],
  [/\bcreature\b|\bwolf\b|\banimal\b/i, "creature"],
  [/\bflower\b|\bgarden\b|\bgrass\b/i, "grass"],
  [/\brock\b|\bstone\b|\bmonolith\b/i, "rock"],
];

const COLORS: Record<string, string> = {
  violet: "#9a7cff",
  purple: "#8b5cf6",
  blue: "#5b8cff",
  cyan: "#5de4e0",
  teal: "#39c9b0",
  green: "#5cd68a",
  emerald: "#31c48d",
  gold: "#f2c96d",
  amber: "#f0a34a",
  orange: "#f28a52",
  red: "#e56767",
  crimson: "#c34a6a",
  rose: "#e58aa8",
  pink: "#e77fb1",
  white: "#e9edff",
  silver: "#b9c5db",
  moon: "#cfe0ff",
};

function clamp01(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.min(1, Math.max(0, value));
}

function attribute(value: unknown, provenance: string, confidence: number): SceneAttribute {
  return { value, confidence, provenance, locked: false, renderable: true };
}

function lerpHex(from: string, to: string, amount: number): string {
  const parse = (hex: string) => {
    const normalized = hex.replace("#", "");
    return [
      Number.parseInt(normalized.slice(0, 2), 16),
      Number.parseInt(normalized.slice(2, 4), 16),
      Number.parseInt(normalized.slice(4, 6), 16),
    ];
  };
  const a = parse(from);
  const b = parse(to);
  const mix = (index: number) => Math.round(a[index] + (b[index] - a[index]) * clamp01(amount));
  return `#${mix(0).toString(16).padStart(2, "0")}${mix(1).toString(16).padStart(2, "0")}${mix(2)
    .toString(16)
    .padStart(2, "0")}`;
}

function promptColor(prompt: string, fallback: string): string {
  const lower = prompt.toLowerCase();
  for (const [word, color] of Object.entries(COLORS)) {
    if (lower.includes(word)) return color;
  }
  return fallback;
}

function hintedKinds(prompt: string): string[] {
  const kinds: string[] = [];
  for (const [pattern, kind] of KIND_HINTS) {
    if (pattern.test(prompt) && !kinds.includes(kind)) kinds.push(kind);
  }
  return kinds;
}

function paletteFor(signals: ImagineSignals, prompt: string, style: ImagineStyle) {
  const warm = signals.valence >= 0.5;
  const accent = promptColor(prompt, warm ? "#f0b27a" : "#7bd8e8");
  const top = warm
    ? lerpHex("#190f24", "#3b1f3b", signals.arousal)
    : lerpHex("#06101c", "#13233c", signals.arousal);
  const horizon = warm
    ? lerpHex("#8a4e62", "#f0a37a", signals.vividness)
    : lerpHex("#234b68", "#70c8d8", signals.vividness);
  const bottom = warm ? "#100b16" : "#04070d";
  const gothic = style === "gothic";
  return {
    accent,
    top,
    horizon,
    bottom,
    key: gothic ? "#d7a0ff" : accent,
    rim: warm ? "#ff7e9c" : "#62f0d1",
    ambient: warm ? "#3a2638" : "#1b3048",
  };
}

function entity(
  id: string,
  kind: string,
  label: string,
  role: string,
  position: Vec3,
  scale: number,
  color: string,
  accent: string,
  emissive: number,
  signals: ImagineSignals,
): SceneEntity {
  return {
    id,
    kind,
    label,
    role,
    transform: { position, rotation: [0, 0, 0] as Vec3, scale: [scale, scale, scale] as Vec3 },
    attributes: {
      color: attribute(color, "local_procedural", signals.confidence),
      secondary_color: attribute(accent, "local_procedural", signals.confidence),
      size: attribute(scale, "local_procedural", signals.confidence),
      emissive: attribute(emissive, "local_procedural", signals.confidence),
      opacity: attribute(1, "local_procedural", signals.confidence),
      symbolic: attribute(true, "local_procedural", 1),
    },
    confidence: signals.confidence,
    provenance: "local_procedural",
    locked: false,
    visible: true,
    parent_id: null,
  };
}

export function promptFingerprint(brief: ImagineBrief, signals: ImagineSignals): number {
  return fnv1a(
    `${brief.prompt}|${brief.style}|${brief.seed}|${Object.values(signals)
      .map((value) => value.toFixed(3))
      .join(",")}`,
  );
}

export function buildLegacyImagineScene(brief: ImagineBrief, signals: ImagineSignals): SceneGraph {
  const palette = paletteFor(signals, brief.prompt, brief.style);
  const seed = promptFingerprint(brief, signals);
  const random = mulberry32(seed);
  const tuning = STYLE_TUNING[brief.style];
  const hints = hintedKinds(brief.prompt);
  const count = Math.max(6, Math.min(13, Math.round(6 + signals.vividness * 5 + signals.attention * 2)));
  const kinds = ["portal", "water", ...hints, "crystal", "tree", "rock", "grass", "door"];
  const uniqueKinds = [...new Set(kinds)];
  const entities: SceneEntity[] = [];
  const portalId = "imagine:portal";
  const emitter = 0.35 + signals.vividness * 0.9 + signals.gamma * 0.4;

  entities.push(
    entity(
      portalId,
      "portal",
      "Threshold",
      "subject",
      [0, 1.35, -18],
      1.55 + signals.vividness * 0.45,
      palette.accent,
      palette.rim,
      emitter,
      signals,
    ),
  );

  for (let index = 0; index < count; index += 1) {
    const kind = uniqueKinds[index % uniqueKinds.length];
    if (kind === "portal") continue;
    const side = index % 2 === 0 ? -1 : 1;
    const z = -2.6 - index * 1.75 - random() * 0.5;
    const x = side * (2.1 + random() * 1.5 + (1 - signals.attention) * 1.2);
    const y = kind === "water" ? -0.02 : 0;
    const scale = 0.55 + random() * 0.45 + signals.vividness * 0.25;
    entities.push(
      entity(
        `imagine:${kind}:${index}`,
        kind,
        `${STYLE_LABELS[brief.style]} ${kind}`,
        "background",
        [x, y, z],
        scale,
        kind === "water" ? palette.horizon : palette.accent,
        palette.rim,
        kind === "fire" || kind === "crystal" ? emitter : emitter * 0.45,
        signals,
      ),
    );
  }

  const relations = entities
    .filter((entry) => entry.id !== portalId)
    .slice(0, 7)
    .map((entry, index) => ({
      subject_id: entry.id,
      relation: index % 2 === 0 ? "in_front_of" : "around",
      object_id: portalId,
      confidence: signals.confidence,
      provenance: "local_procedural",
    }));

  const fog = clamp01(tuning.fog + signals.fatigue * 0.05 + signals.theta * 0.02 - signals.confidence * 0.008);
  const stars = Math.round(
    Math.max(0, tuning.stars * (0.45 + signals.confidence * 0.8) * (1 - signals.fatigue * 0.6)),
  );
  const warm = signals.valence >= 0.5;

  return {
    scene_id: `imagine:${seed.toString(16)}`,
    version: 1,
    seed,
    title: "Latent corridor · local preview",
    version_tag: "IMAGINA-IMAGINE-local-v1",
    entities,
    relations,
    style: brief.style,
    camera: {
      position: [0, 1.68, 7.5],
      target: [0, 1.35, -5],
      fov: 70,
      motion: "static",
      speed: 0,
    },
    lighting: {
      key: { color: palette.key, intensity: tuning.key + signals.vividness * 0.5, direction: [4, 8, 5] },
      ambient: { color: palette.ambient, intensity: 0.26 + signals.alpha * 0.25 },
      rim: { color: palette.rim, intensity: 0.45 + signals.arousal * 1.1 },
    },
    atmosphere: {
      fog: { color: warm ? "#1a1424" : "#08131d", density: Math.min(0.11, fog) },
      sky: {
        top: palette.top,
        horizon: palette.horizon,
        bottom: palette.bottom,
        stars,
        aurora: tuning.aurora && signals.valence > 0.55,
      },
      weather: signals.fatigue > 0.58 ? "drifting haze" : "still air",
      time_of_day: warm ? "late dusk" : "blue hour",
    },
    dynamics: {
      wind: 0.12 + signals.arousal * 0.55,
      water: 0.1 + signals.alpha * 0.4,
      fire: 0.15 + signals.beta * 0.45,
      floating: 0.2 + signals.theta * 0.65,
      pulse: 0.08 + signals.gamma * 0.7 + signals.arousal * 0.25,
    },
    constraints: [],
    metadata: {
      engine: "local-procedural",
      diffusion_status: "disconnected",
      prompt: brief.prompt,
      adaptive: "preview",
      first_person: true,
      signal_vector: { ...signals },
      claim_ceiling: "L1_BEHAVIORAL_ASSISTED",
      warnings: [
        "Local procedural fallback. No diffusion model is running.",
        "The signal vector is a demo control surface, not a measurement from a person.",
      ],
    },
  };
}

export function buildImagineScene(brief: ImagineBrief, signals: ImagineSignals): SceneGraph {
  const world = deriveWorldSpec({
    prompt: brief.prompt,
    style: brief.style,
    seed: brief.seed,
    title: brief.title,
    signals,
  });
  return composeImagineWorld(brief, world, signals, promptFingerprint(brief, signals));
}

export function describeImagineScene(scene: SceneGraph): string {
  const count = scene.entities.length;
  const boundary =
    "This is a symbolic first-person preview generated locally from a text brief and a demo signal vector. It is not a reconstruction of anyone's imagery.";
  return `${scene.title}. ${count} symbolic element${count === 1 ? "" : "s"}. ${scene.atmosphere.weather}, ${scene.atmosphere.time_of_day}. ${boundary}`;
}

export function signalCoherence(signals: ImagineSignals, target: AdaptiveTarget): number {
  const values = Object.entries(target.target) as Array<[ImagineChannelId, number]>;
  const distance =
    values.reduce((total, [key, goal]) => total + Math.abs(clamp01(signals[key]) - goal), 0) / values.length;
  return clamp01(1 - distance);
}

export function stepAdaptiveSignals(
  current: ImagineSignals,
  target: AdaptiveTarget,
  rate = 0.18,
): ImagineSignals {
  const next = { ...current };
  for (const [key, goal] of Object.entries(target.target) as Array<[ImagineChannelId, number]>) {
    next[key] = clamp01(current[key] + (goal - current[key]) * rate);
  }
  next.hrv = clamp01(current.hrv + (target.target.confidence - current.hrv) * rate * 0.35);
  next.eda = clamp01(current.eda + (target.target.arousal - current.eda) * rate * 0.35);
  next.alpha = clamp01(current.alpha + (target.target.valence - current.alpha) * rate * 0.25);
  next.theta = clamp01(current.theta + (target.target.fatigue - current.theta) * rate * 0.25);
  next.beta = clamp01(current.beta + (target.target.attention - current.beta) * rate * 0.25);
  next.gamma = clamp01(current.gamma + (target.target.vividness - current.gamma) * rate * 0.25);
  return next;
}

export function buildDiffusionJob(
  brief: ImagineBrief,
  signals: ImagineSignals,
  target: AdaptiveTarget | null,
): DiffusionJob {
  return {
    schema: "IMAGINA-DIFFUSION-JOB-v1",
    status: "blocked",
    engine: "latent-scene-diffusion",
    blocker: "No A100 worker is attached. This is a handoff contract, not a run.",
    model: {
      slot: "scene-diffusion-v0",
      candidate: "SDXL-Turbo + depth/segmentation ControlNet (proposal, not evaluated)",
      precision: "fp16",
      minimumVramGb: 40,
    },
    prompt: brief.prompt.trim(),
    negativePrompt:
      "photorealistic face, readable text, clinical imagery, diagnostic diagram, reconstruction claim",
    conditioning: {
      text: true,
      depth: true,
      segmentation: true,
      signalVector: { ...signals },
      adaptiveTarget: target?.id ?? null,
      firstPerson: true,
    },
    render: {
      width: 1280,
      height: 720,
      steps: 6,
      guidance: 1.8,
      seed: promptFingerprint(brief, signals),
      fps: 24,
    },
    output: {
      format: "scene_graph+preview",
      firstPerson: true,
      adaptationHz: 0.5,
    },
    boundary:
      "Proposed pipeline. No diffusion weights, remote pod, or generated image are present in this build.",
  };
}

export function styleLabel(style: ImagineStyle): string {
  return STYLE_LABELS[style];
}
