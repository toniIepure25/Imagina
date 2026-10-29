import type { ImagineStyle } from "@/lib/imagineScene";

export interface ImaginePreset {
  id: string;
  title: string;
  subtitle: string;
  description: string;
  prompt: string;
  style: ImagineStyle;
  seed: string;
  preview: {
    from: string;
    via: string;
    to: string;
    accent: string;
  };
}

export const IMAGINE_PRESETS: ImaginePreset[] = [
  {
    id: "grove",
    title: "Bioluminescent Grove",
    subtitle: "Grove · fireflies · night",
    description: "A walkable grove of elder trees, drifting motes, and a soft threshold in the distance.",
    prompt: "A quiet bioluminescent grove with fireflies, elder trees, and a distant glowing door under a violet sky.",
    style: "dream",
    seed: "lumen-grove",
    preview: { from: "#04120f", via: "#18584a", to: "#020706", accent: "#7cf0cf" },
  },
  {
    id: "observatory",
    title: "Drowned Observatory",
    subtitle: "Observatory · mist · dusk",
    description: "A brass dome above shallow water, meridian piers, and a low horizon.",
    prompt: "A drowned observatory on a dark coast, with a brass dome, meridian piers, and a still pool at dusk.",
    style: "cinematic",
    seed: "lumen-observatory",
    preview: { from: "#071021", via: "#2b3f68", to: "#03060d", accent: "#9fb4ff" },
  },
  {
    id: "library",
    title: "Gothic Library",
    subtitle: "Interior · library · blue hour",
    description: "Shelf walls, reading tables, suspended lamps, and a lit portal between the stacks.",
    prompt: "A gothic library at blue hour, with tall shelf walls, reading tables, suspended lamps, and a single lit portal.",
    style: "gothic",
    seed: "lumen-library",
    preview: { from: "#0e0a11", via: "#4a3138", to: "#050305", accent: "#f4b45f" },
  },
  {
    id: "coast",
    title: "Salt Coast",
    subtitle: "Coast · threshold · dusk",
    description: "A lone gate above a shallow shore, framed by pier stones and a wide sky.",
    prompt: "A salt coast at dusk, with a lone gate above shallow water, pier stones, and a wide warm sky.",
    style: "cinematic",
    seed: "lumen-coast",
    preview: { from: "#0a1620", via: "#b56a52", to: "#04070c", accent: "#f0b27a" },
  },
  {
    id: "void",
    title: "Void Garden",
    subtitle: "Void · garden · night",
    description: "Floating monoliths and pale crystal flowers around a quiet gate in open space.",
    prompt: "A void garden of floating monoliths, pale crystal flowers, and a quiet gate under a deep star field.",
    style: "surreal",
    seed: "lumen-void",
    preview: { from: "#080615", via: "#3a2d6b", to: "#020104", accent: "#b49cff" },
  },
];

export function presetById(id: string | null | undefined): ImaginePreset | null {
  if (!id) return null;
  return IMAGINE_PRESETS.find((preset) => preset.id === id) ?? null;
}
