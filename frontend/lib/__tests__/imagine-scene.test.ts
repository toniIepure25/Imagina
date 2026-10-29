import { describe, expect, it } from "vitest";
import {
  ADAPTIVE_TARGETS,
  DEFAULT_BRIEF,
  DEFAULT_SIGNALS,
  buildDiffusionJob,
  buildImagineScene,
  describeImagineScene,
  signalCoherence,
  stepAdaptiveSignals,
} from "@/lib/imagineScene";

const target = ADAPTIVE_TARGETS.find((item) => item.id === "calm")!;

describe("first-person local scene synthesis", () => {
  it("is deterministic for the same brief and signal vector", () => {
    const first = buildImagineScene(DEFAULT_BRIEF, DEFAULT_SIGNALS);
    const second = buildImagineScene(DEFAULT_BRIEF, DEFAULT_SIGNALS);
    expect(first).toEqual(second);
    expect(first.seed).toBe(second.seed);
    expect(first.entities.length).toBeGreaterThanOrEqual(18);
  });

  it("builds a first-person camera and symbolic provenance", () => {
    const scene = buildImagineScene(DEFAULT_BRIEF, DEFAULT_SIGNALS);
    expect(scene.camera.position).toEqual([0, 1.72, 6.4]);
    expect(scene.camera.fov).toBe(70);
    expect(scene.camera.motion).toBe("static");
    expect(scene.metadata.engine).toBe("lumen-procedural");
    expect(scene.metadata.diffusion_status).toBe("disconnected");
    expect(scene.entities.every((entity) => entity.provenance === "local_procedural")).toBe(true);
  });

  it("maps fatigue to fog and valence to a different horizon", () => {
    const calm = buildImagineScene(DEFAULT_BRIEF, { ...DEFAULT_SIGNALS, fatigue: 0.1 });
    const tired = buildImagineScene(DEFAULT_BRIEF, { ...DEFAULT_SIGNALS, fatigue: 0.9 });
    expect(tired.atmosphere.fog.density).toBeGreaterThan(calm.atmosphere.fog.density);

    const cool = buildImagineScene(DEFAULT_BRIEF, { ...DEFAULT_SIGNALS, valence: 0.1 });
    const warm = buildImagineScene(DEFAULT_BRIEF, { ...DEFAULT_SIGNALS, valence: 0.9 });
    expect(cool.atmosphere.sky.horizon).not.toBe(warm.atmosphere.sky.horizon);
  });

  it("uses prompt terms as symbolic kinds and exposes a boundary", () => {
    const scene = buildImagineScene(
      { ...DEFAULT_BRIEF, prompt: "A forest door beside a pool of water and a crystal" },
      DEFAULT_SIGNALS,
    );
    const kinds = new Set(scene.entities.map((entity) => entity.kind));
    expect(kinds.has("tree")).toBe(true);
    expect(kinds.has("door")).toBe(true);
    expect(kinds.has("water")).toBe(true);
    expect(kinds.has("crystal")).toBe(true);
    expect(describeImagineScene(scene)).toContain("not a reconstruction");
  });

  it("produces a blocked diffusion handoff rather than pretending to run one", () => {
    const job = buildDiffusionJob(DEFAULT_BRIEF, DEFAULT_SIGNALS, target);
    expect(job.schema).toBe("IMAGINA-DIFFUSION-JOB-v1");
    expect(job.status).toBe("blocked");
    expect(job.blocker).toContain("No A100 worker");
    expect(job.boundary).toContain("No diffusion weights");
    expect(job.conditioning.firstPerson).toBe(true);
    expect(job.conditioning.signalVector).toEqual(DEFAULT_SIGNALS);
    expect(job.conditioning.adaptiveTarget).toBe("calm");
  });

  it("moves the demo vector toward the adaptive target and raises coherence", () => {
    const start = { ...DEFAULT_SIGNALS, arousal: 0.9, fatigue: 0.8 };
    const before = signalCoherence(start, target);
    let next = start;
    for (let index = 0; index < 20; index += 1) next = stepAdaptiveSignals(next, target);
    expect(signalCoherence(next, target)).toBeGreaterThan(before);
    expect(next.arousal).toBeLessThan(start.arousal);
    expect(next.fatigue).toBeLessThan(start.fatigue);
    expect(next.arousal).toBeGreaterThanOrEqual(0);
    expect(next.fatigue).toBeLessThanOrEqual(1);
  });
});
