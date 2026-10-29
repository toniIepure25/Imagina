"use client";

import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import type { SceneGraph } from "@/lib/animusStudioApi";
import type { WorldSpec } from "@/lib/imagine/world";
import { entityColor } from "../sceneUtils";

const SKY_VERTEX = `
varying vec3 vDirection;
void main() {
  vDirection = normalize(position);
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`;

const SKY_FRAGMENT = `
varying vec3 vDirection;
uniform vec3 topColor;
uniform vec3 horizonColor;
uniform vec3 bottomColor;
uniform vec3 sunColor;
uniform vec3 sunDirection;
uniform float sunStrength;
uniform float aurora;
uniform float haze;

void main() {
  vec3 direction = normalize(vDirection);
  float h = direction.y;
  vec3 color = mix(bottomColor, horizonColor, smoothstep(-0.5, 0.1, h));
  color = mix(color, topColor, smoothstep(0.02, 0.7, h));

  float sun = max(dot(direction, normalize(sunDirection)), 0.0);
  color += sunColor * pow(sun, 420.0) * sunStrength * 2.4;
  color += sunColor * pow(sun, 12.0) * sunStrength * 0.16;

  if (aurora > 0.01) {
    float angle = atan(direction.z, direction.x);
    float band = sin(angle * 3.2 + h * 9.0) * 0.5 + 0.5;
    float curtain = smoothstep(0.08, 0.38, h) * (1.0 - smoothstep(0.42, 0.72, h));
    color += mix(vec3(0.16, 0.86, 0.68), vec3(0.44, 0.5, 1.0), band) * band * curtain * aurora * 0.34;
  }

  color += horizonColor * haze * (1.0 - smoothstep(-0.08, 0.2, h)) * 0.25;
  gl_FragColor = vec4(color, 1.0);
}
`;

const TERRAIN_VERTEX = `
varying vec2 vUv;
varying vec3 vWorld;
void main() {
  vUv = uv;
  vec4 world = modelMatrix * vec4(position, 1.0);
  vWorld = world.xyz;
  gl_Position = projectionMatrix * viewMatrix * world;
}
`;

const TERRAIN_FRAGMENT = `
varying vec2 vUv;
varying vec3 vWorld;
uniform vec3 groundColor;
uniform vec3 pathColor;
uniform vec3 accentColor;
uniform float pathWidth;
uniform float pathReach;

float hash(vec2 p) {
  p = fract(p * vec2(123.34, 456.21));
  p += dot(p, p + 45.32);
  return fract(p.x * p.y);
}

float noise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  f = f * f * (3.0 - 2.0 * f);
  float a = hash(i);
  float b = hash(i + vec2(1.0, 0.0));
  float c = hash(i + vec2(0.0, 1.0));
  float d = hash(i + vec2(1.0, 1.0));
  return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}

void main() {
  float grain = noise(vWorld.xz * 0.32) * 0.5 + noise(vWorld.xz * 1.4) * 0.22;
  vec3 color = mix(groundColor, groundColor * 1.28 + accentColor * 0.045, grain);
  float inPath = 1.0 - smoothstep(pathWidth * 0.38, pathWidth * 0.62, abs(vWorld.x));
  inPath *= smoothstep(-pathReach - 1.6, -pathReach + 1.2, vWorld.z);
  inPath *= 1.0 - smoothstep(5.4, 8.2, vWorld.z);
  color = mix(color, pathColor, inPath * 0.76);
  float edge = smoothstep(pathWidth * 0.4, pathWidth * 0.48, abs(vWorld.x)) *
    (1.0 - smoothstep(pathWidth * 0.48, pathWidth * 0.56, abs(vWorld.x)));
  color += accentColor * edge * inPath * 0.12;
  float vignette = 1.0 - smoothstep(18.0, 42.0, length(vWorld.xz));
  color *= 0.72 + vignette * 0.28;
  gl_FragColor = vec4(color, 1.0);
}
`;

export function WorldSky({ scene, world }: { scene: SceneGraph; world: WorldSpec }) {
  const uniforms = useMemo(
    () => ({
      topColor: { value: new THREE.Color(scene.atmosphere.sky.top) },
      horizonColor: { value: new THREE.Color(scene.atmosphere.sky.horizon) },
      bottomColor: { value: new THREE.Color(scene.atmosphere.sky.bottom) },
      sunColor: { value: new THREE.Color(world.timeOfDay === "night" ? "#dfe8ff" : world.palette.rim) },
      sunDirection: { value: new THREE.Vector3(-0.55, world.timeOfDay === "day" ? 0.62 : 0.24, -0.78) },
      sunStrength: {
        value: world.timeOfDay === "night" ? 0.55 : world.timeOfDay === "dusk" ? 0.9 : 1.1,
      },
      aurora: { value: scene.atmosphere.sky.aurora ? 0.45 + world.emissiveBudget * 0.55 : 0 },
      haze: { value: 0.5 + world.fog * 0.8 },
    }),
    [scene.atmosphere.sky, world],
  );

  return (
    <mesh scale={[90, 90, 90]} renderOrder={-10}>
      <sphereGeometry args={[1, 48, 32]} />
      <shaderMaterial
        side={THREE.BackSide}
        depthWrite={false}
        toneMapped={false}
        vertexShader={SKY_VERTEX}
        fragmentShader={SKY_FRAGMENT}
        uniforms={uniforms}
      />
    </mesh>
  );
}

export function WorldTerrain({ world }: { world: WorldSpec }) {
  const uniforms = useMemo(
    () => ({
      groundColor: { value: new THREE.Color(world.palette.ground) },
      pathColor: { value: new THREE.Color(world.palette.ground).multiplyScalar(1.35) },
      accentColor: { value: new THREE.Color(world.palette.accent) },
      pathWidth: { value: world.path.width },
      pathReach: { value: Math.abs(world.path.end[2]) },
    }),
    [world],
  );

  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.03, -6]} receiveShadow>
      <planeGeometry args={[90, 90, 1, 1]} />
      <shaderMaterial vertexShader={TERRAIN_VERTEX} fragmentShader={TERRAIN_FRAGMENT} uniforms={uniforms} />
    </mesh>
  );
}

export function PracticalLights({ scene, world }: { scene: SceneGraph; world: WorldSpec }) {
  const lights = useMemo(
    () =>
      scene.entities
        .filter((entity) => ["lantern", "portal", "shrine", "crystal"].includes(entity.kind))
        .slice(0, 3)
        .map((entity) => ({
          id: entity.id,
          color: entityColor(entity),
          position: [
            entity.transform.position[0],
            entity.transform.position[1] + 0.6,
            entity.transform.position[2],
          ] as [number, number, number],
          intensity: entity.kind === "portal" ? 2.2 : 0.85,
        })),
    [scene.entities],
  );

  return (
    <>
      {lights.map((light) => (
        <pointLight
          key={light.id}
          color={light.color}
          position={light.position}
          intensity={light.intensity * (0.65 + world.emissiveBudget * 0.5)}
          distance={light.intensity > 1 ? 15 : 7}
          decay={2}
        />
      ))}
    </>
  );
}

export function AmbientMotes({ scene, world, animate }: { scene: SceneGraph; world: WorldSpec; animate: boolean }) {
  const count = world.biome === "void" ? 150 : 90;
  const positions = useMemo(() => {
    const values = new Float32Array(count * 3);
    for (let index = 0; index < count; index += 1) {
      const angle = index * 2.399;
      const radius = 3 + (index % 11) * 1.4;
      values[index * 3] = Math.cos(angle) * radius;
      values[index * 3 + 1] = 0.4 + (index % 9) * 0.6;
      values[index * 3 + 2] = -2 - (index % 13) * 1.4;
    }
    return values;
  }, [count]);
  const ref = useRef<THREE.Points>(null);

  useFrame(({ clock }) => {
    if (!ref.current || !animate) return;
    ref.current.rotation.y = clock.getElapsedTime() * 0.006;
    ref.current.position.y = Math.sin(clock.getElapsedTime() * 0.12) * 0.08;
  });

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial
        color={scene.atmosphere.sky.aurora ? world.palette.accent : world.palette.rim}
        size={world.biome === "void" ? 0.075 : 0.055}
        sizeAttenuation
        transparent
        opacity={0.55}
        depthWrite={false}
        toneMapped={false}
      />
    </points>
  );
}
