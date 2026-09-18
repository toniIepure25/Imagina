import { describe, it, expect } from "vitest";

describe("animusApi", () => {
  it("exports session functions", async () => {
    const mod = await import("../animusApi");
    expect(typeof mod.createSession).toBe("function");
    expect(typeof mod.generateCandidate).toBe("function");
    expect(typeof mod.sendFeedback).toBe("function");
    expect(typeof mod.stepSession).toBe("function");
    expect(typeof mod.getTimeline).toBe("function");
    expect(typeof mod.stopSession).toBe("function");
  });

  it("exposes attribute directions and object choices", async () => {
    const { ATTRIBUTE_DIRECTIONS, OBJECT_CHOICES } = await import("../animusApi");
    expect(ATTRIBUTE_DIRECTIONS.length).toBeGreaterThan(3);
    expect(ATTRIBUTE_DIRECTIONS.every((d) => d.direction && d.label)).toBe(true);
    expect(OBJECT_CHOICES).toContain("castle");
  });
});
