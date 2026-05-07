import { FeedbackAction } from "./types";

export interface SceneParams {
  clarity: number;
  blur: number;
  wallDistortion: number;
  lightStability: number;
  textureDetail: number;
  particleStability: number;
  doorComplexity: number;
  fogDensity: number;
  colorSaturation: number;
  breathingCueStrength: number;
}

export const DEFAULT_SCENE_PARAMS: SceneParams = {
  clarity: 0.3,
  blur: 0.5,
  wallDistortion: 0.5,
  lightStability: 0.4,
  textureDetail: 0.0,
  particleStability: 0.4,
  doorComplexity: 0.0,
  fogDensity: 0.5,
  colorSaturation: 0.3,
  breathingCueStrength: 0.3,
};

export function feedbackToScene(fb: FeedbackAction): SceneParams {
  return {
    clarity: fb.scene_clarity,
    blur: fb.blur,
    wallDistortion: fb.wall_distortion,
    lightStability: fb.light_stability,
    textureDetail: fb.texture_detail,
    particleStability: fb.particle_stability,
    doorComplexity: fb.door_complexity,
    fogDensity: fb.fog_density,
    colorSaturation: fb.color_saturation,
    breathingCueStrength: fb.breathing_cue_strength,
  };
}
