import { describe, expect, it } from "vitest";
import { buildRandomizationPreview, fnv1a, mulberry32 } from "@/lib/randomization";

describe("randomization preview", () => {
  it("hashes deterministically", () => {
    expect(fnv1a("IMAGINA")).toBe(fnv1a("IMAGINA"));
    expect(fnv1a("IMAGINA")).not.toBe(fnv1a("imagina"));
  });

  it("produces deterministic sequences for the same input", () => {
    const input = { seed: "local", blocks: 4, blockLength: 3, scheme: "block" as const };
    const first = buildRandomizationPreview(input);
    const second = buildRandomizationPreview(input);
    expect(first).toEqual(second);
    expect(first.sequence).toHaveLength(24);
  });

  it("keeps blocks balanced and reports imbalance", () => {
    const preview = buildRandomizationPreview({ seed: "balanced", blocks: 5, blockLength: 4, scheme: "block" });
    expect(preview.perCondition.a).toBe(20);
    expect(preview.perCondition.b).toBe(20);
    expect(preview.imbalance).toBe(0);
    expect(preview.sequence).toHaveLength(40);
  });

  it("alternates mirrored blocks for counterbalance", () => {
    const preview = buildRandomizationPreview({
      seed: "mirror",
      blocks: 2,
      blockLength: 2,
      scheme: "counterbalance",
    });
    expect(preview.sequence).toHaveLength(8);
    expect(preview.sequence.slice(0, 4)).toEqual(["A", "A", "B", "B"]);
    expect(preview.sequence.slice(4)).toEqual(["B", "B", "A", "A"]);
  });

  it("clamps unsafe input and keeps the RNG in range", () => {
    const preview = buildRandomizationPreview({ seed: "x", blocks: 0, blockLength: 0, scheme: "block" });
    expect(preview.blocks).toBe(1);
    expect(preview.blockLength).toBe(1);
    expect(preview.sequence).toHaveLength(2);

    const random = mulberry32(42);
    for (let index = 0; index < 32; index += 1) {
      const value = random();
      expect(value).toBeGreaterThanOrEqual(0);
      expect(value).toBeLessThan(1);
    }
  });
});
