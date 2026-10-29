import type { SceneGraph } from "@/lib/animusStudioApi";
import type { ImagineBrief, ImagineSignals } from "@/lib/imagineScene";
import { promptFingerprint } from "@/lib/imagineScene";
import type { ImagineConditioning, ImagineControls, ImagineDiffusionRequest } from "./types";

export interface RequestInput {
  brief: ImagineBrief;
  negativePrompt?: string;
  conditioning: ImagineConditioning;
  controls: ImagineControls;
  scene: SceneGraph;
  target: "calm" | "immersion" | "exploration";
  signals: ImagineSignals;
}

export function requestIdFor(input: RequestInput): string {
  const fingerprint = promptFingerprint(input.brief, input.signals).toString(16).padStart(8, "0");
  return `req-${input.conditioning.vectorHash.slice(0, 12)}-${fingerprint}`;
}

export function buildDiffusionRequestV2(input: RequestInput): ImagineDiffusionRequest {
  const { vector } = input.conditioning;
  return {
    schema: "IMAGINA-DIFFUSION-REQUEST-v2",
    requestId: requestIdFor(input),
    brief: {
      prompt: input.brief.prompt,
      negative_prompt: input.negativePrompt ?? "people, faces, text, watermark",
      style: input.brief.style,
      seed: input.brief.seed,
    },
    conditioning: {
      schema: "IMAGINA-CONDITIONING-v1",
      adapter: "conditioning-v0",
      source: input.conditioning.source,
      vector: { ...vector },
      quality: vector.signal_quality,
      uncertainty: vector.uncertainty,
      trend: vector.trend,
      stability: vector.stability,
      vector_hash: input.conditioning.vectorHash,
    },
    controls: { ...input.controls },
    camera: {
      mode: "first_person",
      path: [
        {
          position: input.scene.camera.position,
          target: input.scene.camera.target,
        },
      ],
      start: input.scene.camera.position,
      fov: input.scene.camera.fov,
    },
    adaptive: { target: input.target, hz: 0.2 },
    output: {
      skybox: { width: 4096, height: 2048 },
      preview: { width: 1280, height: 720 },
      materials: false,
    },
    provenance: {
      composer_version: "imagine-2.0",
      policy_version: "adaptive-v0",
      app_version: "2.0.0",
    },
    boundary:
      "Generated environment texture; an aesthetic aid, not a reconstruction, measurement, or validated imagery score.",
  };
}
