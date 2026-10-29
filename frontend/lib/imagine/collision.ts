import type { Vec3 } from "@/lib/animusStudioApi";

export interface CameraObstacle {
  x: number;
  z: number;
  radius: number;
}

export interface CameraBounds {
  minX: number;
  maxX: number;
  minZ: number;
  maxZ: number;
}

export const DEFAULT_CAMERA_BOUNDS: CameraBounds = {
  minX: -13,
  maxX: 13,
  minZ: -21,
  maxZ: 10,
};

const CAMERA_RADIUS = 0.34;

function inside(position: { x: number; z: number }, obstacle: CameraObstacle): boolean {
  const dx = position.x - obstacle.x;
  const dz = position.z - obstacle.z;
  return dx * dx + dz * dz < (obstacle.radius + CAMERA_RADIUS) ** 2;
}

export function resolveCameraMove(
  current: Vec3,
  delta: Vec3,
  obstacles: CameraObstacle[] = [],
  bounds: CameraBounds = DEFAULT_CAMERA_BOUNDS,
): Vec3 {
  const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));
  const target = {
    x: clamp(current[0] + delta[0], bounds.minX, bounds.maxX),
    z: clamp(current[2] + delta[2], bounds.minZ, bounds.maxZ),
  };
  const next = { x: target.x, z: target.z };

  for (const obstacle of obstacles) {
    if (!inside(next, obstacle)) continue;
    const slideX = { x: current[0], z: next.z };
    if (!inside(slideX, obstacle)) {
      next.x = current[0];
      continue;
    }
    const slideZ = { x: next.x, z: current[2] };
    if (!inside(slideZ, obstacle)) {
      next.z = current[2];
      continue;
    }
    next.x = current[0];
    next.z = current[2];
  }

  return [next.x, current[1], next.z];
}
