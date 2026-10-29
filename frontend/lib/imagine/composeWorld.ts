import type { SceneAttribute, SceneEntity, SceneGraph, Vec3 } from "@/lib/animusStudioApi";
import type { WorldLayerId, WorldSpec } from "./world";

export type ComposeInput = {
  prompt: string;
  style: string;
  seed: string;
  signals: {
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
  };
};

type EntitySpec = {
  kind: string;
  label: string;
  role: string;
  position: Vec3;
  scale: number | Vec3;
  color: string;
  accent: string;
  emissive: number;
  layer: WorldLayerId;
  collidable: boolean;
  source: string;
  anchor: string;
  variant: number;
};

const FOCAL_KIND: Record<string, string> = {
  shelves: "library",
  gate: "portal",
  bridge: "bridge",
  moon: "moon",
  tree: "tree",
  tower: "castle",
  water: "water",
  altar: "shrine",
  dome: "observatory",
  crystal: "crystal",
  column: "colonnade",
};

const FOCAL_SCALE: Record<string, number> = {
  library: 2.2,
  portal: 1.7,
  door: 1.4,
  bridge: 3.4,
  moon: 2.8,
  tree: 2.5,
  castle: 1.4,
  water: 3.6,
  shrine: 1.8,
  observatory: 1.4,
  crystal: 1.4,
  colonnade: 1.2,
};

const HORIZON_KIND: Record<WorldSpec["biome"], string> = {
  grove: "mountain",
  coast: "mountain",
  interior: "cloud",
  ruin: "mountain",
  observatory: "mountain",
  void: "crystal",
};

function sceneAttribute(value: unknown, source: string, confidence: number): SceneAttribute {
  return {
    value,
    confidence,
    provenance: "local_procedural",
    locked: false,
    renderable: true,
    source_text: source,
  };
}

function asVec3(scale: number | Vec3): Vec3 {
  return typeof scale === "number" ? [scale, scale, scale] : scale;
}

function makeEntity(spec: EntitySpec, signals: ComposeInput["signals"], index: number): SceneEntity {
  const scale = asVec3(spec.scale);
  return {
    id: `imagine:${spec.layer}:${spec.kind}:${index}`,
    kind: spec.kind,
    label: spec.label,
    role: spec.role,
    transform: {
      position: spec.position,
      rotation: [0, spec.anchor.includes("left") ? 0.12 : spec.anchor.includes("right") ? -0.12 : 0, 0],
      scale,
    },
    attributes: {
      color: sceneAttribute(spec.color, spec.source, signals.confidence),
      secondary_color: sceneAttribute(spec.accent, spec.source, signals.confidence),
      size: sceneAttribute(scale[0], spec.source, signals.confidence),
      emissive: sceneAttribute(spec.emissive, spec.source, signals.confidence),
      opacity: sceneAttribute(1, spec.source, signals.confidence),
      symbolic: sceneAttribute(true, "archetype", 1),
      semantic_source: sceneAttribute(spec.source, spec.source, signals.confidence),
      layer: sceneAttribute(spec.layer, spec.source, signals.confidence),
      collidable: sceneAttribute(spec.collidable, spec.source, signals.confidence),
      variant: sceneAttribute(spec.variant, spec.source, signals.confidence),
      anchor: sceneAttribute(spec.anchor, spec.source, signals.confidence),
    },
    confidence: signals.confidence,
    provenance: "local_procedural",
    locked: false,
    visible: true,
    parent_id: null,
  };
}

function focalScale(kind: string): number {
  return FOCAL_SCALE[kind] ?? 2.2;
}

function addFocal(specs: EntitySpec[], world: WorldSpec, signals: ComposeInput["signals"], prompt: string) {
  const doorOnly = world.focal.kind === "gate" && /\bdoor\b/i.test(prompt) && !/\b(gate|gateway|portal)\b/i.test(prompt);
  const kind = doorOnly ? "door" : FOCAL_KIND[world.focal.kind] ?? "portal";
  specs.push({
    kind,
    label: world.focal.label,
    role: "subject",
    position: [0, kind === "moon" ? world.focal.height : 0, -world.focal.distance],
    scale: focalScale(kind),
    color: world.palette.accent,
    accent: world.palette.rim,
    emissive: 0.35 + world.emissiveBudget * 0.95,
    layer: "threshold",
    collidable: true,
    source: `prompt:${world.focal.label.toLowerCase()}`,
    anchor: "focal",
    variant: 0,
  });
}

function addArchitecture(
  specs: EntitySpec[],
  world: WorldSpec,
  signals: ComposeInput["signals"],
  detail: number,
) {
  const { palette, archetype } = world;
  const source = `archetype:${archetype}`;

  if (archetype === "library") {
    for (const side of [-1, 1]) {
      for (let index = 0; index < 2; index += 1) {
        specs.push({
          kind: "library",
          label: index === 0 ? "Near shelf wall" : "Far shelf wall",
          role: "frame",
          position: [side * 4.8, 0, -6.4 - index * 4.2],
          scale: [1.8, 1, 0.9],
          color: palette.ground,
          accent: palette.accent,
          emissive: 0.08,
          layer: "flank",
          collidable: true,
          source,
          anchor: side < 0 ? "flank-left" : "flank-right",
          variant: index,
        });
      }
      specs.push({
        kind: "table",
        label: "Reading table",
        role: "prop",
        position: [side * 2.7, 0.47, -5.1 - Math.abs(side) * 0.3],
        scale: [1, 1, 1],
        color: palette.horizon,
        accent: palette.rim,
        emissive: 0.04,
        layer: "midground",
        collidable: true,
        source,
        anchor: side < 0 ? "mid-left" : "mid-right",
        variant: 0,
      });
      specs.push({
        kind: "lantern",
        label: "Suspended lamp",
        role: "light",
        position: [side * 2.2, 2.6, -8.6],
        scale: 0.34,
        color: palette.rim,
        accent: palette.accent,
        emissive: 0.7 + world.emissiveBudget * 0.5,
        layer: "detail",
        collidable: false,
        source: "style:gothic",
        anchor: side < 0 ? "light-left" : "light-right",
        variant: 0,
      });
    }
  }

  if (archetype === "threshold") {
    for (const side of [-1, 1]) {
      specs.push({
        kind: "column",
        label: "Gate pier",
        role: "frame",
        position: [side * 3.6, 0, -12.4],
        scale: [0.55, 1, 0.55],
        color: palette.ground,
        accent: palette.accent,
        emissive: 0.1,
        layer: "flank",
        collidable: true,
        source,
        anchor: side < 0 ? "flank-left" : "flank-right",
        variant: 0,
      });
    }
  }

  if (archetype === "colonnade" || world.biome === "ruin") {
    for (const side of [-1, 1]) {
      for (let index = 0; index < 3; index += 1) {
        specs.push({
          kind: "column",
          label: world.biome === "ruin" ? "Broken column" : "Colonnade column",
          role: "frame",
          position: [side * (3.4 + index * 0.1), 0, -4.8 - index * 3.4],
          scale: [0.5, 1, 0.5],
          color: palette.ground,
          accent: palette.rim,
          emissive: 0.04,
          layer: index === 2 ? "horizon" : "flank",
          collidable: true,
          source,
          anchor: side < 0 ? "flank-left" : "flank-right",
          variant: index,
        });
      }
    }
  }

  if (archetype === "bridge") {
    specs.push({
      kind: "bridge",
      label: "Processional bridge",
      role: "frame",
      position: [0, 0.05, -5.2],
      scale: [3.4, 0.45, 7.4],
      color: palette.ground,
      accent: palette.rim,
      emissive: 0.02,
      layer: "approach",
      collidable: false,
      source,
      anchor: "approach",
      variant: 0,
    });
  }

  if (archetype === "garden") {
    const treeCount = 3 + Math.round(detail * 2);
    for (let index = 0; index < treeCount; index += 1) {
      const side = index % 2 === 0 ? -1 : 1;
      specs.push({
        kind: "tree",
        label: index === 0 ? "Threshold tree" : "Garden tree",
        role: "frame",
        position: [side * (3.9 + (index % 3) * 1.2), 0, -4.2 - index * 2.6],
        scale: 1.2 + (index % 3) * 0.28,
        color: palette.ground,
        accent: palette.accent,
        emissive: 0.04,
        layer: index < 3 ? "flank" : "midground",
        collidable: true,
        source,
        anchor: side < 0 ? "flank-left" : "flank-right",
        variant: index,
      });
    }
  }

  if (archetype === "observatory") {
    for (let index = 0; index < 4; index += 1) {
      const side = index % 2 === 0 ? -1 : 1;
      specs.push({
        kind: "column",
        label: "Meridian pier",
        role: "frame",
        position: [side * (3.2 + Math.floor(index / 2) * 0.9), 0, -7.4 - Math.floor(index / 2) * 4.2],
        scale: [0.42, 1, 0.42],
        color: palette.ground,
        accent: palette.accent,
        emissive: 0.08,
        layer: "flank",
        collidable: true,
        source,
        anchor: side < 0 ? "flank-left" : "flank-right",
        variant: index,
      });
    }
    specs.push({
      kind: "ring",
      label: "Instrument ring",
      role: "prop",
      position: [0, 1.9, -9.6],
      scale: 1.2,
      color: palette.accent,
      accent: palette.rim,
      emissive: 0.28,
      layer: "midground",
      collidable: false,
      source,
      anchor: "center",
      variant: 0,
    });
  }

  if (archetype === "citadel") {
    for (const side of [-1, 1]) {
      specs.push({
        kind: "castle",
        label: "Outer tower",
        role: "frame",
        position: [side * 7.4, 0, -11.4],
        scale: 0.8,
        color: palette.ground,
        accent: palette.rim,
        emissive: 0.06,
        layer: "flank",
        collidable: true,
        source,
        anchor: side < 0 ? "flank-left" : "flank-right",
        variant: 0,
      });
    }
  }
}

function addBiomeProps(
  specs: EntitySpec[],
  world: WorldSpec,
  signals: ComposeInput["signals"],
  detail: number,
) {
  const { palette, biome } = world;
  const source = `biome:${biome}`;

  if (biome === "coast" || biome === "observatory") {
    specs.push({
      kind: "water",
      label: "Shallow water",
      role: "ground",
      position: [0, -0.04, -8.6],
      scale: [11, 0.05, 13],
      color: palette.horizon,
      accent: palette.accent,
      emissive: 0.02,
      layer: "midground",
      collidable: false,
      source,
      anchor: "ground",
      variant: 0,
    });
  }

  if (biome === "grove" || biome === "ruin") {
    const count = 3 + Math.round(detail * 4);
    for (let index = 0; index < count; index += 1) {
      const side = index % 2 === 0 ? -1 : 1;
      specs.push({
        kind: index % 3 === 0 ? "rock" : "grass",
        label: index % 3 === 0 ? "Moss stone" : "Ground cover",
        role: "detail",
        position: [side * (2.45 + (index % 4) * 0.85), 0, -2.4 - index * 1.4],
        scale: index % 3 === 0 ? 0.38 + (index % 3) * 0.12 : 0.32,
        color: palette.ground,
        accent: palette.accent,
        emissive: 0.02,
        layer: "detail",
        collidable: false,
        source,
        anchor: side < 0 ? "detail-left" : "detail-right",
        variant: index,
      });
    }
  }

  if (biome === "void") {
    for (let index = 0; index < 3 + Math.round(detail * 3); index += 1) {
      const side = index % 2 === 0 ? -1 : 1;
      specs.push({
        kind: index % 2 === 0 ? "crystal" : "monolith",
        label: index % 2 === 0 ? "Floating prism" : "Void monolith",
        role: "detail",
        position: [
          side * (4.2 + (index % 3) * 1.8),
          index % 2 === 0 ? 0.9 + (index % 3) * 0.8 : 0,
          -5.4 - index * 2.2,
        ],
        scale: 0.7 + (index % 3) * 0.4,
        color: palette.accent,
        accent: palette.rim,
        emissive: 0.2 + signals.gamma * 0.35,
        layer: "detail",
        collidable: false,
        source,
        anchor: side < 0 ? "detail-left" : "detail-right",
        variant: index,
      });
    }
  }
}

function addGenericProps(specs: EntitySpec[], world: WorldSpec) {
  const { palette } = world;
  for (const side of [-1, 1]) {
    specs.push({
      kind: "lantern",
      label: "Path lantern",
      role: "light",
      position: [side * 3.1, 0, -6.8],
      scale: 1,
      color: palette.rim,
      accent: palette.accent,
      emissive: 0.45 + world.emissiveBudget * 0.45,
      layer: "midground",
      collidable: false,
      source: "archetype:approach",
      anchor: side < 0 ? "light-left" : "light-right",
      variant: 0,
    });
    specs.push({
      kind: "rock",
      label: "Path stone",
      role: "detail",
      position: [side * 5.2, 0, -9.2],
      scale: 0.55,
      color: palette.ground,
      accent: palette.horizon,
      emissive: 0.01,
      layer: "detail",
      collidable: true,
      source: `biome:${world.biome}`,
      anchor: side < 0 ? "detail-left" : "detail-right",
      variant: 0,
    });
  }
}

function addGroundDetail(specs: EntitySpec[], world: WorldSpec, detail: number) {
  const count = 4 + Math.round(detail * 5);
  const indoor = world.biome === "interior" || world.biome === "void" || world.biome === "observatory";
  for (let index = 0; index < count; index += 1) {
    const side = index % 2 === 0 ? -1 : 1;
    specs.push({
      kind: indoor ? "mote" : index % 4 === 0 ? "flower" : "grass",
      label: indoor ? "Light mote" : "Ground detail",
      role: "detail",
      position: [side * (2.35 + (index % 3) * 0.9), indoor ? 0.7 + (index % 3) * 0.5 : 0, -2.6 - index * 1.55],
      scale: indoor ? 0.12 : 0.28,
      color: indoor ? world.palette.accent : world.palette.ground,
      accent: world.palette.rim,
      emissive: indoor ? 0.55 : 0.01,
      layer: "detail",
      collidable: false,
      source: `signal:detail:${detail.toFixed(2)}`,
      anchor: side < 0 ? "detail-left" : "detail-right",
      variant: index,
    });
  }
}

function addPromptProps(specs: EntitySpec[], world: WorldSpec, prompt: string) {
  const has = (kind: string) => specs.some((spec) => spec.kind === kind);
  if (/\b(tree|forest|grove|wood)\b/i.test(prompt) && !has("tree")) {
    for (const side of [-1, 1]) {
      specs.push({
        kind: "tree",
        label: "Prompt tree",
        role: "frame",
        position: [side * 4.4, 0, -6.6 + side * 0.4],
        scale: 1.35,
        color: world.palette.ground,
        accent: world.palette.accent,
        emissive: 0.03,
        layer: "flank",
        collidable: true,
        source: "prompt:tree",
        anchor: side < 0 ? "flank-left" : "flank-right",
        variant: 0,
      });
    }
  }
  if (/\b(water|pool|lake|river|ocean|sea)\b/i.test(prompt) && !has("water")) {
    specs.push({
      kind: "water",
      label: "Prompt water",
      role: "ground",
      position: [0, -0.04, -8.8],
      scale: [8, 0.04, 9],
      color: world.palette.horizon,
      accent: world.palette.accent,
      emissive: 0.02,
      layer: "midground",
      collidable: false,
      source: "prompt:water",
      anchor: "ground",
      variant: 0,
    });
  }
  if (/\b(crystal|prism|glass)\b/i.test(prompt) && !has("crystal")) {
    for (const side of [-1, 1]) {
      specs.push({
        kind: "crystal",
        label: "Prompt crystal",
        role: "detail",
        position: [side * 3.8, 0.7, -8.2],
        scale: 0.55,
        color: world.palette.accent,
        accent: world.palette.rim,
        emissive: 0.4,
        layer: "detail",
        collidable: true,
        source: "prompt:crystal",
        anchor: side < 0 ? "detail-left" : "detail-right",
        variant: 0,
      });
    }
  }
}

function addHorizon(specs: EntitySpec[], world: WorldSpec) {
  const { palette } = world;
  const count = world.biome === "void" ? 2 : 3;
  for (let index = 0; index < count; index += 1) {
    const side = index % 2 === 0 ? -1 : 1;
    specs.push({
      kind: HORIZON_KIND[world.biome],
      label: "Distant silhouette",
      role: "horizon",
      position: [side * (11 + index * 4), 0, -34 - index * 5],
      scale: 7 + index * 1.8,
      color: palette.bottom,
      accent: palette.horizon,
      emissive: 0.01,
      layer: "horizon",
      collidable: false,
      source: `biome:${world.biome}`,
      anchor: side < 0 ? "horizon-left" : "horizon-right",
      variant: index,
    });
  }

  if (world.timeOfDay === "night" || world.timeOfDay === "dusk") {
    specs.push({
      kind: world.timeOfDay === "night" ? "moon" : "sun",
      label: world.timeOfDay === "night" ? "Moon" : "Low sun",
      role: "horizon",
      position: [-8.5, 8.4, -36],
      scale: 1.5,
      color: world.timeOfDay === "night" ? "#dfe8ff" : "#ffd7a0",
      accent: palette.rim,
      emissive: 0.8,
      layer: "horizon",
      collidable: false,
      source: `time:${world.timeOfDay}`,
      anchor: "horizon-left",
      variant: 0,
    });
  }
}

function addAtmosphere(specs: EntitySpec[], world: WorldSpec) {
  if (world.weather !== "fireflies" && world.weather !== "embers") return;
  const count = 6 + Math.round(world.detailBudget * 6);
  for (let index = 0; index < count; index += 1) {
    const side = index % 2 === 0 ? -1 : 1;
    specs.push({
      kind: "firefly",
      label: world.weather === "embers" ? "Ember mote" : "Firefly mote",
      role: "detail",
      position: [side * (1.2 + (index % 5) * 0.9), 0.5 + (index % 4) * 0.7, -1.5 - index * 1.1],
      scale: 0.14,
      color: world.weather === "embers" ? "#ff9c5a" : "#c9ff8a",
      accent: world.palette.accent,
      emissive: 0.9,
      layer: "detail",
      collidable: false,
      source: `weather:${world.weather}`,
      anchor: "detail-center",
      variant: index,
    });
  }
}

export function composeImagineWorld(
  brief: { prompt: string; style: string; seed: string },
  world: WorldSpec,
  signals: ComposeInput["signals"],
  seed: number,
): SceneGraph {
  const specs: EntitySpec[] = [];
  addFocal(specs, world, signals, brief.prompt);
  specs.push({
    kind: "path",
    label: "Approach path",
    role: "ground",
    position: [0, 0.01, -5.2],
    scale: [world.path.width, 1, 15.4],
    color: world.palette.ground,
    accent: world.palette.horizon,
    emissive: 0,
    layer: "approach",
    collidable: false,
    source: "archetype:approach",
    anchor: "approach",
    variant: 0,
  });
  addArchitecture(specs, world, signals, world.detailBudget);
  addBiomeProps(specs, world, signals, world.detailBudget);
  addPromptProps(specs, world, brief.prompt);
  addGenericProps(specs, world);
  addGroundDetail(specs, world, world.detailBudget);
  addHorizon(specs, world);
  addAtmosphere(specs, world);

  const limitedSpecs = specs.slice(0, 40);
  const entities = limitedSpecs.map((spec, index) => makeEntity(spec, signals, index));
  const focalId = entities[0]?.id ?? "imagine:threshold";

  const relations = entities
    .filter((entry) => entry.id !== focalId && entry.role !== "ground")
    .slice(0, 10)
    .map((entry, index) => ({
      subject_id: entry.id,
      relation: index % 2 === 0 ? "in_front_of" : "beside",
      object_id: focalId,
      confidence: signals.confidence,
      provenance: "local_procedural",
    }));

  const stars = Math.round(
    Math.max(0, (world.timeOfDay === "night" ? 780 : world.timeOfDay === "dusk" ? 360 : 120) * (1 - world.fog * 0.65)),
  );
  const weather =
    world.weather === "rain" || world.weather === "snow"
      ? world.weather
      : world.weather === "fireflies" || world.weather === "embers"
        ? "still air"
        : world.weather;

  return {
    scene_id: `imagine:${seed.toString(16)}`,
    version: 1,
    seed,
    title: world.title,
    version_tag: "IMAGINA-IMAGINE-local-v2",
    entities,
    relations,
    style: brief.style,
    camera: {
      position: [...world.camera.spawn] as Vec3,
      target: [...world.camera.target] as Vec3,
      fov: world.camera.fov,
      motion: "static",
      speed: 0,
    },
    lighting: {
      key: {
        color: world.palette.key,
        intensity: 0.95 + signals.vividness * 0.6 + (world.timeOfDay === "day" ? 0.2 : 0),
        direction: [4, 8, 5],
      },
      ambient: { color: world.palette.ambient, intensity: 0.24 + signals.alpha * 0.24 },
      rim: { color: world.palette.rim, intensity: 0.4 + signals.arousal * 1.05 },
    },
    atmosphere: {
      fog: {
        color: world.palette.bottom,
        density: Math.min(0.11, 0.008 + world.fog * 0.075),
      },
      sky: {
        top: world.palette.top,
        horizon: world.palette.horizon,
        bottom: world.palette.bottom,
        stars,
        aurora: world.biome === "void" || world.biome === "observatory" || world.weather === "fireflies",
      },
      weather,
      time_of_day: world.timeOfDay,
    },
    dynamics: {
      wind: 0.1 + signals.arousal * 0.5,
      water: 0.1 + signals.alpha * 0.4,
      fire: 0.12 + signals.beta * 0.4,
      floating: 0.16 + signals.theta * 0.6,
      pulse: 0.06 + signals.gamma * 0.65 + signals.arousal * 0.2,
    },
    constraints: [
      {
        kind: "keep_clear",
        target: focalId,
        value: { path_width: world.path.width, spawn: world.camera.spawn },
        strength: 1,
        provenance: "local_procedural",
      },
    ],
    metadata: {
      engine: "lumen-procedural",
      diffusion_status: "disconnected",
      prompt: brief.prompt,
      adaptive: "preview",
      first_person: true,
      signal_vector: { ...signals },
      claim_ceiling: "L1_BEHAVIORAL_ASSISTED",
      world,
      composition: {
        layers: world.layers.map((layer) => layer.id),
        focal: world.focal,
        path: world.path,
        entity_count: entities.length,
        truncated: specs.length > limitedSpecs.length,
      },
      warnings: [
        "Local Lumen composition. No diffusion model is running.",
        "The signal vector is a demo control surface, not a measurement from a person.",
      ],
    },
  };
}
