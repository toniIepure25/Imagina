export const SCENE_RELATIONS = [
  "above",
  "below",
  "left_of",
  "right_of",
  "behind",
  "in_front_of",
  "next_to",
  "around",
] as const;

export type SceneRelationName = (typeof SCENE_RELATIONS)[number];

export const POSITION_LIMIT = 256;
export const SCALE_MIN = 0.01;
export const SCALE_MAX = 64;

export function clampPosition(value: number): number {
  return Math.max(-POSITION_LIMIT, Math.min(POSITION_LIMIT, value));
}

export function clampScale(value: number): number {
  return Math.max(SCALE_MIN, Math.min(SCALE_MAX, value));
}

export function isSceneRelation(value: string): value is SceneRelationName {
  return (SCENE_RELATIONS as readonly string[]).includes(value);
}

const PROVENANCE_LABELS: Record<string, string> = {
  user_explicit: "your edit",
  user_implied: "from intention",
  candidate: "candidate",
  seed: "seed",
  procedural: "procedural",
  generator: "procedural",
  lock: "locked",
  undo: "undo",
  redo: "redo",
  branch: "branch",
};

export function provenanceLabel(provenance: string | null | undefined): string {
  if (!provenance) return "unknown source";
  return PROVENANCE_LABELS[provenance] ?? provenance.replace(/_/g, " ");
}

export function relationLabel(relation: string): string {
  return relation.replace(/_/g, " ");
}

export function isUserProvenance(provenance: string | null | undefined): boolean {
  return provenance === "user_explicit" || provenance === "user_implied";
}
