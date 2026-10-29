import { describe, expect, it } from "vitest";
import { ADAPTIVE_TARGETS, DEFAULT_BRIEF, DEFAULT_SIGNALS, buildImagineScene } from "@/lib/imagineScene";
import { buildConditioning, deriveControls } from "@/lib/imagine/conditioning";
import { buildDiffusionRequestV2, requestIdFor } from "@/lib/imagine/request";
import { manifestAssetUrl } from "@/lib/imagine/manifest";

const target = ADAPTIVE_TARGETS.find((item) => item.id === "immersion")!;

function build() {
  const conditioning = buildConditioning(DEFAULT_SIGNALS);
  const controls = deriveControls(conditioning);
  return {
    brief: DEFAULT_BRIEF,
    negativePrompt: "people",
    conditioning,
    controls,
    scene: buildImagineScene(DEFAULT_BRIEF, DEFAULT_SIGNALS),
    target: target.id,
    signals: DEFAULT_SIGNALS,
  };
}

describe("diffusion request v2", () => {
  it("carries text, 16D conditioning, controls, and a first-person camera", () => {
    const input = build();
    const request = buildDiffusionRequestV2(input);
    expect(request.schema).toBe("IMAGINA-DIFFUSION-REQUEST-v2");
    expect(request.requestId).toBe(requestIdFor(input));
    expect(request.brief.negative_prompt).toBe("people");
    expect(Object.keys(request.conditioning.vector)).toHaveLength(16);
    expect(request.camera.mode).toBe("first_person");
    expect(request.output.skybox).toEqual({ width: 4096, height: 2048 });
    expect(request.boundary).toContain("not a reconstruction");
  });

  it("does not contain raw signal arrays or session identifiers", () => {
    const serialized = JSON.stringify(buildDiffusionRequestV2(build()));
    expect(serialized).not.toContain("session_id");
    expect(serialized).not.toContain("raw_signals");
    expect(serialized).not.toContain("eeg_samples");
  });

  it("resolves a manifest asset against the local API", () => {
    expect(
      manifestAssetUrl(
        { url: "/animus/imagine/assets/skybox-12345678", width: 1, height: 1, sha256: "a".repeat(64) },
        "http://localhost:8000",
      ),
    ).toBe("http://localhost:8000/animus/imagine/assets/skybox-12345678");
  });
});
