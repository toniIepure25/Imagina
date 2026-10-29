import { describe, expect, it } from "vitest";
import {
  SCENE_RELATIONS,
  clampPosition,
  clampScale,
  isSceneRelation,
  provenanceLabel,
} from "@/lib/sceneContract";

describe("sceneContract", () => {
  it("mirrors the eight backend relations", () => {
    expect(SCENE_RELATIONS).toHaveLength(8);
    expect(isSceneRelation("in_front_of")).toBe(true);
    expect(isSceneRelation("inside")).toBe(false);
  });

  it("clamps positions and scales to the backend limits", () => {
    expect(clampPosition(999)).toBe(256);
    expect(clampPosition(-999)).toBe(-256);
    expect(clampScale(0)).toBe(0.01);
    expect(clampScale(999)).toBe(64);
  });

  it("labels provenance without making a causal claim", () => {
    expect(provenanceLabel("user_explicit")).toBe("your edit");
    expect(provenanceLabel("seed")).toBe("seed");
    expect(provenanceLabel(null)).toBe("unknown source");
  });
});
