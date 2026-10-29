import { describe, expect, it } from "vitest";
import {
  deriveWorldSpec,
  type WorldInput,
  type WorldSignalVector,
  type WorldStyle,
} from "@/lib/imagine/world";

const SIGNALS: WorldSignalVector = {
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

function input(overrides: Partial<WorldInput> = {}): WorldInput {
  return {
    prompt: "A quiet bioluminescent corridor under a violet sky, with a distant door",
    style: "dream",
    seed: "imagina-first-person",
    signals: SIGNALS,
    ...overrides,
  };
}

describe("deriveWorldSpec", () => {
  it("reads a gothic library as an interior library", () => {
    const world = deriveWorldSpec(input({ prompt: "a gothic library at blue hour", style: "gothic" }));
    expect(world.biome).toBe("interior");
    expect(world.archetype).toBe("library");
    expect(world.focal.kind).toBe("shelves");
    expect(world.title).toContain("Library");
    expect(world.timeOfDay).toBe("dusk");
  });

  it("reads an ocean gate as a coastal threshold", () => {
    const world = deriveWorldSpec(input({ prompt: "an ocean gate under a warm dusk sky", style: "cinematic" }));
    expect(world.biome).toBe("coast");
    expect(world.archetype).toBe("threshold");
    expect(world.focal.kind).toBe("gate");
    expect(world.timeOfDay).toBe("dusk");
  });

  it("keeps fireflies and a grove from a forest prompt", () => {
    const world = deriveWorldSpec(input({ prompt: "a quiet forest with fireflies and a glowing door" }));
    expect(world.biome).toBe("grove");
    expect(world.weather).toBe("fireflies");
    expect(world.palette.accent).toMatch(/^#[0-9a-f]{6}$/i);
  });

  it("reads an abandoned observatory above a dark sea", () => {
    const world = deriveWorldSpec(input({ prompt: "an abandoned observatory above a dark sea", style: "gothic" }));
    expect(world.biome).toBe("observatory");
    expect(world.archetype).toBe("observatory");
    expect(world.weather).toBe("mist");
  });

  it("falls back deterministically for an empty prompt", () => {
    const first = deriveWorldSpec(input({ prompt: "", style: "minimal" }));
    const second = deriveWorldSpec(input({ prompt: "   ", style: "minimal" }));
    expect(first.biome).toBe("void");
    expect(first.archetype).toBe("threshold");
    expect(first.title).toBeTruthy();
    expect(second).toEqual(first);
  });

  it("keeps semantics stable when only signals change", () => {
    const base = deriveWorldSpec(input());
    const loaded = deriveWorldSpec(
      input({
        signals: {
          ...SIGNALS,
          attention: 0.98,
          arousal: 0.92,
          vividness: 0.95,
          fatigue: 0.76,
          confidence: 0.2,
          signal_quality: 0.25,
        },
      }),
    );
    expect(loaded.biome).toBe(base.biome);
    expect(loaded.archetype).toBe(base.archetype);
    expect(loaded.focal).toEqual(base.focal);
    expect(loaded.layers.map((layer) => layer.id)).toEqual(base.layers.map((layer) => layer.id));
    expect(loaded.detailBudget).not.toBe(base.detailBudget);
    expect(loaded.fog).not.toBe(base.fog);
  });

  it("is deterministic for the same brief and seed", () => {
    expect(deriveWorldSpec(input())).toEqual(deriveWorldSpec(input()));
    expect(deriveWorldSpec(input({ seed: "other" })).seed).not.toBe(deriveWorldSpec(input()).seed);
  });

  it("parses a named color and clamps long prompts", () => {
    const world = deriveWorldSpec(input({ prompt: `violet sky ${"and a door ".repeat(120)}` }));
    expect(world.palette.accent).toBe("#9a7cff");
    expect(world.promptExcerpt.length).toBeLessThanOrEqual(240);
    expect(world.sources.some((source) => source.kind === "prompt")).toBe(true);
  });

  it("exposes a complete palette and layer contract", () => {
    const world = deriveWorldSpec(input());
    for (const color of Object.values(world.palette)) {
      expect(color).toMatch(/^#[0-9a-f]{6}$/i);
    }
    expect(world.layers.map((layer) => layer.id)).toEqual([
      "spawn",
      "approach",
      "threshold",
      "flank",
      "midground",
      "horizon",
      "detail",
    ]);
    expect(world.path.end[2]).toBeLessThan(world.path.start[2]);
    expect(world.camera.spawn[1]).toBeGreaterThan(1);
  });
});

describe("world style priors", () => {
  it("uses distinct archetypes for distinct explicit prompts", () => {
    const cases: Array<[string, WorldStyle, string]> = [
      ["a long bridge over a black river", "cinematic", "bridge"],
      ["a ruined colonnade in the rain", "gothic", "colonnade"],
      ["a floating island in a void", "surreal", "threshold"],
      ["a white castle above the ocean", "cinematic", "citadel"],
    ];
    for (const [prompt, style, archetype] of cases) {
      expect(deriveWorldSpec(input({ prompt, style })).archetype).toBe(archetype);
    }
  });
});
