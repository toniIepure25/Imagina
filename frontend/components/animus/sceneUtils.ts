import type { SceneEntity, SceneGraph } from "@/lib/animusStudioApi";

export function attrValue(entity: SceneEntity, path: string): unknown {
  return entity.attributes[path]?.value;
}

export function attrNumber(entity: SceneEntity, path: string, fallback: number): number {
  const value = attrValue(entity, path);
  if (typeof value === "number" && Number.isFinite(value)) return value;
  return fallback;
}

export function attrString(entity: SceneEntity, path: string, fallback: string): string {
  const value = attrValue(entity, path);
  return typeof value === "string" ? value : fallback;
}

export function attrColor(entity: SceneEntity, path: string, fallback: string): string {
  const value = attrString(entity, path, fallback);
  return /^#[0-9a-f]{6}$/i.test(value) ? value : fallback;
}

export function entityColor(entity: SceneEntity): string {
  return attrColor(entity, "color", "#9aa7c7");
}

export function entityAccent(entity: SceneEntity): string {
  return attrColor(entity, "secondary_color", entityColor(entity));
}

export function entitySize(entity: SceneEntity): number {
  return Math.max(0.15, Math.min(4, attrNumber(entity, "size", 1)));
}

export function entityOpacity(entity: SceneEntity): number {
  return Math.max(0.05, Math.min(1, attrNumber(entity, "opacity", 1)));
}

export function entityEmissive(entity: SceneEntity): number {
  return Math.max(0, Math.min(3, attrNumber(entity, "emissive", 0)));
}

export function isLocked(entity: SceneEntity): boolean {
  return entity.locked || Object.values(entity.attributes).some((attribute) => attribute.locked);
}

export function provenanceColor(provenance: string | null | undefined): string {
  switch (provenance) {
    case "user_explicit":
      return "#6fe3c4";
    case "user_implied":
      return "#9fe8d2";
    case "candidate":
      return "#e8b45a";
    default:
      return "#7f8ba3";
  }
}

export function isEntityLocked(entity: SceneEntity): boolean {
  return entity.locked;
}

export function hasLockedAttributes(entity: SceneEntity): boolean {
  return Object.values(entity.attributes).some((attribute) => attribute.locked);
}

export function lockedAttributePaths(entity: SceneEntity): string[] {
  return Object.entries(entity.attributes)
    .filter(([, attribute]) => attribute.locked)
    .map(([path]) => path);
}

export function scenePalette(scene: SceneGraph): string[] {
  const colors = scene.entities
    .slice()
    .sort((a, b) => (a.role === "subject" ? -1 : b.role === "subject" ? 1 : 0))
    .map((entity) => entityColor(entity));
  return [scene.atmosphere.sky.top, scene.atmosphere.sky.horizon, ...colors].slice(0, 5);
}

export function sceneGradient(scene: SceneGraph): string {
  const palette = scenePalette(scene);
  return `linear-gradient(135deg, ${palette[0]} 0%, ${palette[1]} 45%, ${palette[2] || "#0a0d18"} 100%)`;
}

export function entityKindLabel(kind: string): string {
  return kind
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function formatTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export function formatRelative(value: string): string {
  const date = new Date(value).getTime();
  if (Number.isNaN(date)) return value;
  const seconds = Math.round((Date.now() - date) / 1000);
  if (seconds < 45) return "just now";
  if (seconds < 3600) return `${Math.round(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.round(seconds / 3600)}h ago`;
  return `${Math.round(seconds / 86400)}d ago`;
}

export function clamp(value: number, low: number, high: number): number {
  return Math.max(low, Math.min(high, value));
}

export function hexToRgba(hex: string, alpha: number): string {
  const clean = hex.replace("#", "");
  if (clean.length !== 6) return `rgba(120, 140, 200, ${alpha})`;
  const r = Number.parseInt(clean.slice(0, 2), 16);
  const g = Number.parseInt(clean.slice(2, 4), 16);
  const b = Number.parseInt(clean.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}
