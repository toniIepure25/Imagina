import { fnv1a } from "@/lib/randomization";

export type WorldBiome = "grove" | "coast" | "interior" | "ruin" | "observatory" | "void";
export type WorldArchetype =
  | "threshold"
  | "colonnade"
  | "bridge"
  | "library"
  | "garden"
  | "shrine"
  | "observatory"
  | "citadel";
export type WorldTime = "dawn" | "day" | "dusk" | "night";
export type WorldWeather = "clear" | "mist" | "rain" | "snow" | "embers" | "fireflies";
export type WorldMood = "serene" | "awe" | "melancholy" | "tension" | "wonder";
export type WorldStyle = "dream" | "cinematic" | "gothic" | "surreal" | "minimal";
export type WorldLayerId = "spawn" | "approach" | "threshold" | "flank" | "midground" | "horizon" | "detail";

export interface WorldSignalVector {
  attention: number;
  arousal: number;
  valence: number;
  vividness: number;
  fatigue: number;
  confidence: number;
  theta: number;
  alpha: number;
  beta: number;
  gamma: number;
  hrv: number;
  eda: number;
  signal_quality: number;
}

export interface WorldInput {
  prompt: string;
  style: WorldStyle;
  seed?: string;
  title?: string;
  signals: WorldSignalVector;
}

export interface WorldPalette {
  top: string;
  horizon: string;
  bottom: string;
  ground: string;
  accent: string;
  rim: string;
  key: string;
  ambient: string;
}

export interface WorldLayer {
  id: WorldLayerId;
  label: string;
  purpose: string;
  density: number;
}

export interface WorldSource {
  kind: "prompt" | "archetype" | "style" | "signal";
  token: string;
  weight: number;
}

export interface WorldSpec {
  version: "IMAGINA-WORLD-v1";
  seed: number;
  seedKey: string;
  promptExcerpt: string;
  biome: WorldBiome;
  archetype: WorldArchetype;
  title: string;
  subtitle: string;
  focal: { kind: string; label: string; distance: number; height: number };
  palette: WorldPalette;
  timeOfDay: WorldTime;
  weather: WorldWeather;
  mood: WorldMood;
  detailBudget: number;
  emissiveBudget: number;
  fog: number;
  motion: number;
  stability: number;
  path: { start: [number, number, number]; end: [number, number, number]; width: number };
  camera: { spawn: [number, number, number]; target: [number, number, number]; fov: number; eyeHeight: number };
  layers: WorldLayer[];
  sources: WorldSource[];
}

type Pattern = [RegExp, number];

const BIOME_TERMS: Record<WorldBiome, Pattern[]> = {
  coast: [
    [/\b(ocean|sea|coast|shore|beach|tide|harbou?r|waves?)\b/i, 5],
    [/\b(river|lake|pool|water|reef|island)\b/i, 2],
  ],
  grove: [
    [/\b(forest|grove|wood|woodland|jungle|canopy|moss|fern|thicket)\b/i, 5],
    [/\b(tree|trees|garden|meadow|flower|grass|root)\b/i, 3],
  ],
  interior: [
    [/\b(library|archive|study|scriptorium|reading room|bookshelf|shelves|books)\b/i, 6],
    [/\b(room|hall|corridor|interior|chamber|parlour|parlor|atrium)\b/i, 4],
    [/\b(door|window|lamp|desk)\b/i, 1],
  ],
  ruin: [
    [/\b(ruin|ruined|ruins|broken|crumbled|collapsed|derelict|abandoned)\b/i, 5],
    [/\b(overgrown|decay|rubble|fractured|forgotten)\b/i, 3],
  ],
  observatory: [
    [/\b(observatory|planetarium|telescope|dome|orery|orrery|star chart)\b/i, 6],
    [/\b(cliff|ridge|height|summit|sky deck)\b/i, 2],
  ],
  void: [
    [/\b(void|abyss|cosmic|space|infinite|surreal|liminal|floating|weightless)\b/i, 5],
    [/\b(island|monolith|fragment|nebula|starfield|dream)\b/i, 2],
  ],
};

const ARCHETYPE_TERMS: Record<WorldArchetype, Pattern[]> = {
  threshold: [
    [/\b(gate|gateway|door|doorway|portal|threshold|passage|archway)\b/i, 5],
    [/\b(entrance|opening|arch)\b/i, 2],
  ],
  colonnade: [
    [/\b(colonnade|colonnades|columns?|arcade|peristyle)\b/i, 6],
    [/\b(corridor|hallway|temple|aisle|cloister)\b/i, 3],
  ],
  bridge: [
    [/\b(bridge|span|crossing|viaduct|causeway)\b/i, 6],
  ],
  library: [
    [/\b(library|archive|scriptorium|bookshelf|bookshelves|shelves|books)\b/i, 7],
    [/\b(study|reading room|desk|catalogue|catalog)\b/i, 4],
  ],
  garden: [
    [/\b(garden|grove|meadow|orchard|flower|flowers|greenhouse)\b/i, 5],
    [/\b(forest|trees|canopy|fern)\b/i, 2],
  ],
  shrine: [
    [/\b(shrine|altar|chapel|sanctuary|reliquary|monastery)\b/i, 6],
    [/\b(temple|sacred|offering|vigil)\b/i, 3],
  ],
  citadel: [
    [/\b(castle|citadel|fortress|keep|palace|stronghold)\b/i, 7],
    [/\b(tower|battlement|rampart|throne)\b/i, 4],
  ],
  observatory: [
    [/\b(observatory|planetarium|orrery|telescope)\b/i, 7],
    [/\b(dome|star chart|meridian|equatorial)\b/i, 4],
  ],
};

const STYLE_BIOME: Record<WorldStyle, Partial<Record<WorldBiome, number>>> = {
  dream: { void: 0.8, grove: 0.3 },
  cinematic: { coast: 0.5, ruin: 0.3 },
  gothic: { interior: 0.5, ruin: 0.6 },
  surreal: { void: 1.2, observatory: 0.2 },
  minimal: { interior: 0.4, void: 0.2 },
};

const STYLE_ARCHETYPE: Record<WorldStyle, Partial<Record<WorldArchetype, number>>> = {
  dream: { threshold: 0.3, garden: 0.2 },
  cinematic: { threshold: 0.4, citadel: 0.2 },
  gothic: { library: 0.3, colonnade: 0.5, shrine: 0.4 },
  surreal: { observatory: 0.2, threshold: 0.6 },
  minimal: { threshold: 0.4, colonnade: 0.2 },
};

const COLOR_TERMS: Record<string, string> = {
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
  white: "#e8e4da",
  silver: "#b9c4cc",
  black: "#06070a",
};

const TIME_TERMS: Array<[RegExp, WorldTime]> = [
  [/\b(blue hour|dusk|sunset|evening|twilight)\b/i, "dusk"],
  [/\b(dawn|sunrise|morning|first light)\b/i, "dawn"],
  [/\b(night|midnight|nocturne|moonlit|starlit)\b/i, "night"],
  [/\b(noon|daylight|midday|day)\b/i, "day"],
];

const WEATHER_TERMS: Array<[RegExp, WorldWeather, number]> = [
  [/\b(rain|raining|downpour|rainfall|wet)\b/i, "rain", 5],
  [/\b(snow|snowfall|blizzard|frost)\b/i, "snow", 5],
  [/\b(fog|mist|haze|vapou?r)\b/i, "mist", 4],
  [/\b(ember|embers|ash|sparks?)\b/i, "embers", 4],
  [/\b(firefl|lightning bugs?|glowworms?)\b/i, "fireflies", 5],
  [/\b(clear|cloudless|still air)\b/i, "clear", 2],
  [/\b(abandoned|ruined|forgotten|derelict)\b/i, "mist", 1.4],
  [/\b(dark|shadowed|faint)\b/i, "mist", 0.4],
];

const MOOD_WORDS: Array<[RegExp, WorldMood, number]> = [
  [/\b(quiet|calm|still|serene|gentle|soft)\b/i, "serene", 2],
  [/\b(awe|vast|sublime|monumental|cathedral)\b/i, "awe", 2],
  [/\b(melancholy|sad|grief|lonely|abandoned|faded)\b/i, "melancholy", 2],
  [/\b(tension|unsettling|uncanny|fractured|storm)\b/i, "tension", 2],
  [/\b(wonder|dream|magic|glow|bioluminescent|luminous)\b/i, "wonder", 2],
];

const FOCAL_TERMS: Array<[RegExp, string, string]> = [
  [/\b(shelves|bookshelf|library|archive|books)\b/i, "shelves", "Shelves"],
  [/\b(gate|gateway|door|doorway|portal|threshold|archway)\b/i, "gate", "Threshold gate"],
  [/\b(bridge|span|crossing|viaduct)\b/i, "bridge", "Bridge"],
  [/\b(moon|lunar)\b/i, "moon", "Moon"],
  [/\b(tree|grove|forest|canopy)\b/i, "tree", "Elder tree"],
  [/\b(castle|citadel|fortress|tower|keep)\b/i, "tower", "Tower"],
  [/\b(pool|lake|river|sea|ocean|water)\b/i, "water", "Still water"],
  [/\b(altar|shrine|chapel|sanctuary)\b/i, "altar", "Altar"],
  [/\b(dome|observatory|planetarium|telescope)\b/i, "dome", "Dome"],
  [/\b(crystal|prism|monolith)\b/i, "crystal", "Crystal"],
  [/\b(column|columns|colonnade)\b/i, "column", "Colonnade"],
];

const PALETTES: Record<WorldBiome, WorldPalette> = {
  grove: {
    top: "#051014",
    horizon: "#16483f",
    bottom: "#020706",
    ground: "#0a1b15",
    accent: "#7cf0cf",
    rim: "#f4b45f",
    key: "#d8fff1",
    ambient: "#12352d",
  },
  coast: {
    top: "#06101c",
    horizon: "#235268",
    bottom: "#03070d",
    ground: "#10191c",
    accent: "#7bd8e8",
    rim: "#f0b27a",
    key: "#e8f4ff",
    ambient: "#1b3048",
  },
  interior: {
    top: "#0a0910",
    horizon: "#3b2a31",
    bottom: "#040305",
    ground: "#171313",
    accent: "#f0b27a",
    rim: "#9a7cff",
    key: "#ffd9a8",
    ambient: "#2a1c25",
  },
  ruin: {
    top: "#0b0d0c",
    horizon: "#4b4438",
    bottom: "#050605",
    ground: "#1b1b16",
    accent: "#c9d18c",
    rim: "#d88b5f",
    key: "#fff1cf",
    ambient: "#2c2a20",
  },
  observatory: {
    top: "#040713",
    horizon: "#26365e",
    bottom: "#020309",
    ground: "#0b111d",
    accent: "#9fb4ff",
    rim: "#f2c96d",
    key: "#eef3ff",
    ambient: "#18213b",
  },
  void: {
    top: "#03040b",
    horizon: "#211a42",
    bottom: "#010103",
    ground: "#080711",
    accent: "#b49cff",
    rim: "#7cf0cf",
    key: "#f0eaff",
    ambient: "#18132e",
  },
};

const ARCHETYPE_LABEL: Record<WorldArchetype, string> = {
  threshold: "Threshold",
  colonnade: "Colonnade",
  bridge: "Bridge",
  library: "Library",
  garden: "Garden",
  shrine: "Shrine",
  observatory: "Observatory",
  citadel: "Citadel",
};

const LAYERS: Array<Omit<WorldLayer, "density">> = [
  { id: "spawn", label: "Spawn", purpose: "safe arrival and reading distance" },
  { id: "approach", label: "Approach", purpose: "walkable path into the world" },
  { id: "threshold", label: "Threshold", purpose: "focal object and semantic anchor" },
  { id: "flank", label: "Flank", purpose: "frames that direct the eye" },
  { id: "midground", label: "Midground", purpose: "props and practical light" },
  { id: "horizon", label: "Horizon", purpose: "distant silhouette and scale" },
  { id: "detail", label: "Detail", purpose: "perceptual budget and texture" },
];

function clamp01(value: number): number {
  return Math.max(0, Math.min(1, value));
}

function mixHex(from: string, to: string, amount: number): string {
  const parse = (hex: string) => [1, 3, 5].map((offset) => Number.parseInt(hex.slice(offset, offset + 2), 16));
  const start = parse(from);
  const end = parse(to);
  const mixed = start.map((value, index) => Math.round(value + (end[index] - value) * clamp01(amount)));
  return `#${mixed.map((value) => value.toString(16).padStart(2, "0")).join("")}`;
}

function normalizePrompt(prompt: string): string {
  return prompt.replace(/\s+/g, " ").trim().replace(/[\u2018\u2019]/g, "'").replace(/[\u201c\u201d]/g, '"');
}

function scorePatterns<T extends string>(prompt: string, groups: Record<T, Pattern[]>): Map<T, number> {
  const scores = new Map<T, number>();
  for (const key of Object.keys(groups) as T[]) {
    let score = 0;
    for (const [pattern, weight] of groups[key]) {
      if (pattern.test(prompt)) score += weight;
    }
    scores.set(key, score);
  }
  return scores;
}

function pickMax<T extends string>(scores: Map<T, number>, fallback: T): T {
  let best = fallback;
  let bestScore = -Infinity;
  for (const [key, score] of scores) {
    if (score > bestScore) {
      best = key;
      bestScore = score;
    }
  }
  return bestScore > 0 ? best : fallback;
}

function addPriors<T extends string>(scores: Map<T, number>, priors: Partial<Record<T, number>>) {
  for (const [key, value] of Object.entries(priors) as Array<[T, number]>) {
    scores.set(key, (scores.get(key) ?? 0) + value);
  }
}

function detectTime(prompt: string, style: WorldStyle): WorldTime {
  for (const [pattern, time] of TIME_TERMS) {
    if (pattern.test(prompt)) return time;
  }
  if (style === "gothic") return "night";
  if (style === "dream") return "night";
  if (style === "cinematic") return "dusk";
  return "day";
}

function detectWeather(prompt: string, style: WorldStyle): WorldWeather {
  let weather: WorldWeather = "clear";
  let best = 0;
  for (const [pattern, candidate, weight] of WEATHER_TERMS) {
    if (!pattern.test(prompt)) continue;
    if (weight > best) {
      weather = candidate;
      best = weight;
    }
  }
  if (best > 0) return weather;
  if (style === "dream") return "fireflies";
  if (style === "gothic") return "mist";
  return "clear";
}

function detectMood(prompt: string, signals: WorldSignalVector): WorldMood {
  let mood: WorldMood;
  if (signals.valence >= 0.62 && signals.arousal < 0.55) mood = "serene";
  else if (signals.valence >= 0.65) mood = "awe";
  else if (signals.valence <= 0.35 && signals.arousal >= 0.5) mood = "tension";
  else if (signals.valence <= 0.42) mood = "melancholy";
  else mood = "wonder";

  let best = 0;
  for (const [pattern, candidate, weight] of MOOD_WORDS) {
    if (pattern.test(prompt) && weight > best) {
      mood = candidate;
      best = weight;
    }
  }
  return mood;
}

function detectColor(prompt: string): string | null {
  for (const [name, hex] of Object.entries(COLOR_TERMS)) {
    if (new RegExp(`\\b${name}\\b`, "i").test(prompt)) return hex;
  }
  return null;
}

function detectFocal(prompt: string, archetype: WorldArchetype): { kind: string; label: string } {
  for (const [pattern, kind, label] of FOCAL_TERMS) {
    if (pattern.test(prompt)) return { kind, label };
  }
  if (archetype === "library") return { kind: "shelves", label: "Shelves" };
  if (archetype === "bridge") return { kind: "bridge", label: "Bridge" };
  if (archetype === "colonnade") return { kind: "column", label: "Colonnade" };
  if (archetype === "observatory") return { kind: "dome", label: "Dome" };
  if (archetype === "citadel") return { kind: "tower", label: "Tower" };
  if (archetype === "garden") return { kind: "tree", label: "Elder tree" };
  if (archetype === "shrine") return { kind: "altar", label: "Altar" };
  return { kind: "gate", label: "Threshold gate" };
}

function titleFor(
  prompt: string,
  style: WorldStyle,
  archetype: WorldArchetype,
  time: WorldTime,
  weather: WorldWeather,
): string {
  let adjective = "";
  if (/\b(abandoned|forgotten|derelict)\b/i.test(prompt)) adjective = "Abandoned";
  else if (/\b(quiet|still|calm)\b/i.test(prompt)) adjective = "Quiet";
  else if (/\b(gothic)\b/i.test(prompt) || style === "gothic") adjective = "Gothic";
  else if (weather === "fireflies") adjective = "Firelit";
  else if (weather === "mist") adjective = "Misted";
  else if (weather === "rain") adjective = "Rain-Washed";
  else if (weather === "snow") adjective = "Snowbound";
  else if (weather === "embers") adjective = "Ember";
  else if (time === "dusk") adjective = "Dusk";
  else if (time === "night") adjective = "Nocturne";
  else if (style === "minimal") adjective = "Quiet";
  else if (style === "dream") adjective = "Lucent";
  else if (style === "surreal") adjective = "Uncanny";
  else if (style === "cinematic") adjective = "Cinematic";
  else adjective = "Open";

  return `${adjective} ${ARCHETYPE_LABEL[archetype]}`;
}

export function deriveWorldSpec(input: WorldInput): WorldSpec {
  const prompt = normalizePrompt(input.prompt);
  const seedKey = `${prompt}|${input.style}|${input.seed ?? "imagina-first-person"}`;
  const seed = fnv1a(seedKey);
  const signals = input.signals;

  const biomeScores = scorePatterns(prompt, BIOME_TERMS);
  if (prompt.length > 0) addPriors(biomeScores, STYLE_BIOME[input.style]);
  const biome = prompt.length === 0 ? "void" : pickMax(biomeScores, "void");

  const archetypeScores = scorePatterns(prompt, ARCHETYPE_TERMS);
  if (prompt.length > 0) addPriors(archetypeScores, STYLE_ARCHETYPE[input.style]);
  const archetype = prompt.length === 0 ? "threshold" : pickMax(archetypeScores, "threshold");

  const timeOfDay = detectTime(prompt, input.style);
  const weather = detectWeather(prompt, input.style);
  const mood = detectMood(prompt, signals);
  const focal = detectFocal(prompt, archetype);
  const accent = detectColor(prompt) ?? PALETTES[biome].accent;

  const palette: WorldPalette = {
    ...PALETTES[biome],
    horizon: mixHex(PALETTES[biome].horizon, signals.valence >= 0.5 ? "#b56a52" : "#235268", 0.38),
    accent,
    rim:
      signals.valence >= 0.5
        ? PALETTES[biome].rim
        : signals.arousal > 0.55
          ? "#ff7e9c"
          : PALETTES[biome].rim,
  };

  const detailBudget = clamp01(
    0.24 + signals.attention * 0.34 + signals.vividness * 0.34 + signals.confidence * 0.08,
  );
  const emissiveBudget = clamp01(0.12 + signals.vividness * 0.5 + signals.gamma * 0.26);
  const fog = clamp01(0.12 + signals.fatigue * 0.28 + signals.theta * 0.16 - signals.confidence * 0.04);
  const motion = clamp01(0.12 + signals.arousal * 0.5 + signals.gamma * 0.24 - signals.fatigue * 0.14);
  const stability = clamp01(
    signals.confidence * 0.62 + signals.signal_quality * 0.3 - signals.fatigue * 0.2 + 0.08,
  );

  const layers = LAYERS.map((layer, index) => ({
    ...layer,
    density: clamp01(
      index === 0
        ? 0
        : index === 1
          ? 0.35 + signals.attention * 0.2
          : index === 6
            ? detailBudget
            : 0.3 + detailBudget * 0.55 - index * 0.02,
    ),
  }));

  const sources: WorldSource[] = [];
  for (const [biomeKey, patterns] of Object.entries(BIOME_TERMS) as Array<[WorldBiome, Pattern[]]>) {
    for (const [pattern, weight] of patterns) {
      const match = prompt.match(pattern);
      if (match) sources.push({ kind: "prompt", token: match[0], weight: weight + (biomeKey === biome ? 1 : 0) });
    }
  }
  for (const [archetypeKey, patterns] of Object.entries(ARCHETYPE_TERMS) as Array<[WorldArchetype, Pattern[]]>) {
    for (const [pattern, weight] of patterns) {
      const match = prompt.match(pattern);
      if (match) {
        sources.push({
          kind: "prompt",
          token: match[0],
          weight: weight + (archetypeKey === archetype ? 1 : 0),
        });
      }
    }
  }
  if (prompt.length === 0) {
    sources.push({ kind: "archetype", token: "threshold", weight: 1 });
  }
  sources.push({ kind: "style", token: input.style, weight: 1 });
  sources.push({ kind: "signal", token: `detail:${detailBudget.toFixed(2)}`, weight: detailBudget });
  sources.push({ kind: "signal", token: `emissive:${emissiveBudget.toFixed(2)}`, weight: emissiveBudget });

  return {
    version: "IMAGINA-WORLD-v1",
    seed,
    seedKey,
    promptExcerpt: prompt.slice(0, 240),
    biome,
    archetype,
    title: input.title?.trim() || titleFor(prompt, input.style, archetype, timeOfDay, weather),
    subtitle: `${biome} \u00b7 ${archetype} \u00b7 ${timeOfDay}`,
    focal: { ...focal, distance: 17.6, height: 1.4 },
    palette,
    timeOfDay,
    weather,
    mood,
    detailBudget,
    emissiveBudget,
    fog,
    motion,
    stability,
    path: { start: [0, 0, 6.4], end: [0, 0, -14.4], width: 2.2 + signals.attention * 1.4 },
    camera: {
      spawn: [0, 1.72, 6.4],
      target: [0, 1.34, -5],
      fov: 70,
      eyeHeight: 1.72,
    },
    layers,
    sources,
  };
}
