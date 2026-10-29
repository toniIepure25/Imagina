import { describe, expect, it } from "vitest";
import { isAllowedAssetUrl, validateManifest } from "@/lib/imagine/manifest";
import { resolveCameraMove } from "@/lib/imagine/collision";

const sha = "a".repeat(64);

function manifest(overrides: Record<string, unknown> = {}) {
  return {
    schema: "IMAGINA-DIFFUSION-MANIFEST-v1",
    job_id: "job-12345678",
    state: "succeeded",
    model_slot: "scene-diffusion-v0",
    model_hash: "model-hash",
    seed: 42,
    prompt_hash: "prompt-hash",
    conditioning_hash: "conditioning-hash",
    controls: {},
    skybox: {
      url: "/animus/imagine/assets/skybox-12345678",
      width: 4096,
      height: 2048,
      sha256: sha,
    },
    preview: {
      url: "/animus/imagine/assets/preview-12345678",
      width: 1280,
      height: 720,
      sha256: sha,
    },
    created_at: "2026-10-25T20:00:00Z",
    expires_at: "2099-10-26T20:00:00Z",
    provenance: {},
    ...overrides,
  };
}

describe("diffusion manifest", () => {
  it("accepts a local asset URL and rejects foreign origins", () => {
    expect(isAllowedAssetUrl("/animus/imagine/assets/skybox-12345678", "http://localhost:8000")).toBe(true);
    expect(isAllowedAssetUrl("https://evil.example/animus/imagine/assets/skybox-12345678", "http://localhost:8000")).toBe(
      false,
    );
    expect(isAllowedAssetUrl("http://localhost:8000/api/other", "http://localhost:8000")).toBe(false);
  });

  it("validates a complete manifest", () => {
    const result = validateManifest(manifest(), "http://localhost:8000", Date.parse("2026-10-25T20:00:00Z"));
    expect(result.ok).toBe(true);
  });

  it("rejects expired, foreign, and incomplete manifests", () => {
    expect(validateManifest(manifest(), "http://localhost:8000", Date.parse("2100-01-01T00:00:00Z")).ok).toBe(false);
    expect(
      validateManifest(
        manifest({ skybox: { url: "https://evil.example/x", width: 10, height: 10, sha256: sha } }),
        "http://localhost:8000",
        Date.parse("2026-10-25T20:00:00Z"),
      ).ok,
    ).toBe(false);
    expect(validateManifest({ schema: "unknown" }, "http://localhost:8000").ok).toBe(false);
  });

  it("rejects assets above the declared output dimensions", () => {
    const oversizedSkybox = manifest({
      skybox: { url: "/animus/imagine/assets/skybox-12345678", width: 8192, height: 4096, sha256: sha },
    });
    const oversizedPreview = manifest({
      preview: { url: "/animus/imagine/assets/preview-12345678", width: 1920, height: 1080, sha256: sha },
    });
    const now = Date.parse("2026-10-25T20:00:00Z");
    expect(validateManifest(oversizedSkybox, "http://localhost:8000", now).ok).toBe(false);
    expect(validateManifest(oversizedPreview, "http://localhost:8000", now).ok).toBe(false);
  });
});

describe("camera collision", () => {
  it("slides along an obstacle instead of entering it", () => {
    const next = resolveCameraMove([0, 1.68, 0], [0, 0, 1], [{ x: 0, z: 0.45, radius: 0.5 }]);
    expect(next[2]).toBeLessThan(0.2);
    expect(next[0]).toBe(0);
  });

  it("clamps to corridor bounds", () => {
    const next = resolveCameraMove([12, 1.68, 9], [10, 0, 10]);
    expect(next[0]).toBe(13);
    expect(next[2]).toBe(10);
  });
});
