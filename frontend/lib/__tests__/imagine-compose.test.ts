import { describe, expect, it } from "vitest";
import { buildImagineScene, DEFAULT_BRIEF, DEFAULT_SIGNALS, type ImagineBrief } from "@/lib/imagineScene";
import { IMAGINE_PRESETS, presetById } from "@/lib/imagine/presets";
import type { WorldSpec } from "@/lib/imagine/world";

type SceneWithWorld = ReturnType<typeof buildImagineScene> & {
  metadata: { world: WorldSpec; composition: { entity_count: number } };
};

function sceneFor(brief: Partial<ImagineBrief> = {}, signals = DEFAULT_SIGNALS): SceneWithWorld {
  return buildImagineScene({ ...DEFAULT_BRIEF, ...brief }, signals) as SceneWithWorld;
}

function stat(entity: ReturnType<typeof buildImagineScene>["entities"][number], key: string): unknown {
  return entity.attributes[key]?.value;
}

describe("Lumen composer", () => {
  it("builds a layered world from a brief", () => {
    const scene = sceneFor({ prompt: "a gothic library at blue hour", style: "gothic" });
    expect(scene.title).toContain("Library");
    expect(scene.version_tag).toBe("IMAGINA-IMAGINE-local-v2");
    expect(scene.metadata.engine).toBe("lumen-procedural");
    expect(scene.entities.length).toBeGreaterThanOrEqual(18);
    expect(scene.entities.length).toBeLessThanOrEqual(40);
    expect(scene.metadata.world.layers.map((layer) => layer.id)).toEqual([
      "spawn",
      "approach",
      "threshold",
      "flank",
      "midground",
      "horizon",
      "detail",
    ]);
  });

  it("places the focal object beyond the approach and keeps the path clear", () => {
    const scene = sceneFor({ prompt: "an ocean gate under a dusk sky", style: "cinematic" });
    const focal = scene.entities.find((entity) => entity.role === "subject");
    expect(focal).toBeDefined();
    expect(focal?.transform.position[2]).toBeLessThan(-12);
    const width = scene.metadata.world.path.width;
    for (const entity of scene.entities) {
      if (!stat(entity, "collidable")) continue;
      const z = entity.transform.position[2];
      if (z < -14.2 || z > 6.2) continue;
      expect(Math.abs(entity.transform.position[0])).toBeGreaterThan(width / 2 + 0.3);
    }
  });

  it("records semantic provenance on every entity", () => {
    const scene = sceneFor();
    for (const entity of scene.entities) {
      expect(stat(entity, "semantic_source")).toBeTruthy();
      expect(stat(entity, "layer")).toBeTruthy();
      expect(typeof stat(entity, "collidable")).toBe("boolean");
      expect(stat(entity, "anchor")).toBeTruthy();
      expect(entity.provenance).toBe("local_procedural");
    }
    expect(scene.metadata.world.sources.some((source) => source.kind === "prompt")).toBe(true);
  });

  it("keeps semantics stable while signals change the perceptual budget", () => {
    const calm = sceneFor({ prompt: "a forest with fireflies" });
    const loaded = sceneFor({ prompt: "a forest with fireflies" }, {
      ...DEFAULT_SIGNALS,
      attention: 0.95,
      vividness: 0.9,
      fatigue: 0.7,
      confidence: 0.25,
    });
    expect(loaded.metadata.world.biome).toBe(calm.metadata.world.biome);
    expect(loaded.metadata.world.archetype).toBe(calm.metadata.world.archetype);
    expect(loaded.metadata.world.focal).toEqual(calm.metadata.world.focal);
    expect(loaded.entities.length).toBeGreaterThan(calm.entities.length);
    expect(loaded.seed).not.toBe(calm.seed);
  });

  it("is deterministic and builds every preset", () => {
    const first = sceneFor({ prompt: "a salt coast at dusk" });
    const second = sceneFor({ prompt: "a salt coast at dusk" });
    expect(second).toEqual(first);
    for (const preset of IMAGINE_PRESETS) {
      const scene = sceneFor({ prompt: preset.prompt, style: preset.style, seed: preset.seed, title: preset.title });
      expect(scene.title).toBe(preset.title);
      expect(scene.metadata.world.biome).toBeTruthy();
      expect(scene.entities.length).toBeGreaterThanOrEqual(18);
      expect(scene.entities.some((entity) => entity.role === "subject")).toBe(true);
    }
  });

  it("exposes unique, well-formed presets", () => {
    expect(new Set(IMAGINE_PRESETS.map((preset) => preset.id)).size).toBe(IMAGINE_PRESETS.length);
    expect(presetById("grove")?.title).toBe("Bioluminescent Grove");
    expect(presetById("missing")).toBeNull();
    expect(presetById(null)).toBeNull();
  });

  it("uses architecture-specific props", () => {
    const library = sceneFor({ prompt: "a gothic library", style: "gothic" });
    const observatory = sceneFor({ prompt: "an observatory above a dark coast", style: "cinematic" });
    expect(library.entities.some((entity) => entity.kind === "library")).toBe(true);
    expect(library.entities.some((entity) => entity.kind === "table")).toBe(true);
    expect(observatory.entities.some((entity) => entity.kind === "observatory")).toBe(true);
    expect(observatory.entities.some((entity) => entity.kind === "ring")).toBe(true);
  });
});
