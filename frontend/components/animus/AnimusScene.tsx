"use client";

import { useEffect, useId, useMemo, useRef, useState } from "react";
import { OrbitControls, PerspectiveCamera } from "@react-three/drei";
import { Canvas, useFrame } from "@react-three/fiber";
import * as THREE from "three";
import type { SceneGraph } from "@/lib/animusStudioApi";
import EntityMesh from "./EntityMesh";
import { entityKindLabel } from "./sceneUtils";

const SKY_VERTEX = `
varying vec3 vPos;
void main() {
  vPos = position;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`;

const SKY_FRAGMENT = `
varying vec3 vPos;
uniform vec3 topColor;
uniform vec3 horizonColor;
uniform vec3 bottomColor;
void main() {
  float h = normalize(vPos).y;
  vec3 color = mix(bottomColor, horizonColor, smoothstep(-0.45, 0.12, h));
  color = mix(color, topColor, smoothstep(0.02, 0.72, h));
  gl_FragColor = vec4(color, 1.0);
}
`;

function seeded(index: number, salt: number): number {
  const value = Math.sin(index * 12.9898 + salt * 78.233) * 43758.5453;
  return value - Math.floor(value);
}

function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(query.matches);
    const onChange = (event: MediaQueryListEvent) => setReduced(event.matches);
    query.addEventListener?.("change", onChange);
    return () => query.removeEventListener?.("change", onChange);
  }, []);
  return reduced;
}

function SkyDome({ scene }: { scene: SceneGraph }) {
  const { sky } = scene.atmosphere;
  return (
    <mesh scale={[90, 90, 90]} renderOrder={-10}>
      <sphereGeometry args={[1, 40, 24]} />
      <shaderMaterial
        side={THREE.BackSide}
        depthWrite={false}
        toneMapped={false}
        vertexShader={SKY_VERTEX}
        fragmentShader={SKY_FRAGMENT}
        uniforms={{
          topColor: { value: new THREE.Color(sky.top) },
          horizonColor: { value: new THREE.Color(sky.horizon) },
          bottomColor: { value: new THREE.Color(sky.bottom) },
        }}
      />
    </mesh>
  );
}

function SkyStars({ scene }: { scene: SceneGraph }) {
  const count = Math.max(0, Math.min(2000, Math.round(scene.atmosphere.sky.stars)));
  const positions = useMemo(() => {
    const array = new Float32Array(Math.max(1, count) * 3);
    for (let index = 0; index < count; index += 1) {
      const theta = seeded(index, 1) * Math.PI * 2;
      const phi = Math.acos(0.08 + seeded(index, 2) * 0.92);
      const radius = 48 + seeded(index, 3) * 18;
      array[index * 3] = Math.sin(phi) * Math.cos(theta) * radius;
      array[index * 3 + 1] = Math.cos(phi) * radius;
      array[index * 3 + 2] = Math.sin(phi) * Math.sin(theta) * radius;
    }
    return array;
  }, [count]);

  if (count === 0) return null;
  return (
    <points>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial
        color="#dfe8ff"
        size={0.16}
        sizeAttenuation
        transparent
        opacity={0.8}
        depthWrite={false}
      />
    </points>
  );
}

function Weather({ scene, animate }: { scene: SceneGraph; animate: boolean }) {
  const weather = scene.atmosphere.weather;
  const count = weather === "rain" ? 700 : weather === "snow" ? 450 : 0;
  const positions = useMemo(() => {
    const array = new Float32Array(Math.max(1, count) * 3);
    for (let index = 0; index < count; index += 1) {
      array[index * 3] = (seeded(index, 11) - 0.5) * 30;
      array[index * 3 + 1] = seeded(index, 12) * 18;
      array[index * 3 + 2] = (seeded(index, 13) - 0.5) * 24;
    }
    return array;
  }, [count]);
  const ref = useRef<THREE.Points>(null);

  useFrame(({ clock }) => {
    if (!ref.current || count === 0 || !animate) return;
    const attribute = ref.current.geometry.attributes.position;
    const speed = weather === "rain" ? 0.22 : 0.045;
    for (let index = 0; index < count; index += 1) {
      let y = attribute.getY(index) - speed;
      if (y < 0) y += 18;
      attribute.setY(index, y);
    }
    attribute.needsUpdate = true;
    ref.current.rotation.y = clock.getElapsedTime() * 0.01;
  });

  if (count === 0) return null;
  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial
        color={weather === "rain" ? "#9fc4ff" : "#f4f8ff"}
        size={weather === "rain" ? 0.045 : 0.12}
        transparent
        opacity={0.55}
        depthWrite={false}
      />
    </points>
  );
}

function Ground({ scene }: { scene: SceneGraph }) {
  const color = new THREE.Color(scene.atmosphere.fog.color).multiplyScalar(0.35);
  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.03, 0]} receiveShadow>
      <planeGeometry args={[90, 90, 1, 1]} />
      <meshStandardMaterial color={color} roughness={1} metalness={0} />
    </mesh>
  );
}

function SceneLights({ scene }: { scene: SceneGraph }) {
  const { key, ambient, rim } = scene.lighting;
  return (
    <>
      <ambientLight color={ambient.color} intensity={ambient.intensity} />
      <directionalLight
        color={key.color}
        intensity={key.intensity}
        position={key.direction}
      />
      <pointLight color={rim.color} intensity={rim.intensity} position={[-6, 4, -6]} distance={30} />
    </>
  );
}

function CameraController({ scene }: { scene: SceneGraph }) {
  const { position, fov } = scene.camera;
  return <PerspectiveCamera makeDefault position={position} fov={fov} near={0.05} far={300} />;
}

export default function AnimusScene({
  scene,
  selectedId,
  onSelect,
  className = "",
  showOverlay = true,
  interactive = true,
}: {
  scene: SceneGraph;
  selectedId: string | null;
  onSelect: (entityId: string | null) => void;
  className?: string;
  showOverlay?: boolean;
  interactive?: boolean;
}) {
  const camera = scene.camera;
  const reducedMotion = useReducedMotion();
  const descriptionId = useId();
  const entityLabels = scene.entities.map((entity) => `${entity.label} (${entityKindLabel(entity.kind)})`);
  return (
    <div
      role="region"
      aria-label={interactive ? "Interactive 3D scene preview" : "3D scene preview"}
      aria-describedby={descriptionId}
      className={`relative overflow-hidden bg-[#050711] ${className}`}
      data-testid="animus-scene"
    >
      <p id={descriptionId} className="sr-only" aria-live="polite">
        {showOverlay
          ? `${scene.title}, ${scene.style} style, ${scene.atmosphere.time_of_day}, ${scene.atmosphere.weather}. ${
              entityLabels.length ? `Elements: ${entityLabels.join(", ")}.` : "The scene has no elements yet."
            } Drag to orbit, scroll to zoom, and select an element in the inspector to edit it.`
          : "Scene preview. Visual details are intentionally not described."}
      </p>
      <Canvas
        dpr={[1, 1.7]}
        gl={{ antialias: true, powerPreference: "high-performance" }}
        onPointerMissed={() => onSelect(null)}
      >
        <CameraController scene={scene} />
        <fogExp2 attach="fog" args={[scene.atmosphere.fog.color, Math.min(0.09, scene.atmosphere.fog.density * 2.4)]} />
        <SkyDome scene={scene} />
        <SkyStars scene={scene} />
        <SceneLights scene={scene} />
        <Ground scene={scene} />
        {scene.entities.map((entity) => (
          <EntityMesh
            key={entity.id}
            entity={entity}
            scene={scene}
            selected={selectedId === entity.id}
            onSelect={onSelect}
            animate={!reducedMotion}
          />
        ))}
        <Weather scene={scene} animate={!reducedMotion} />
        <OrbitControls
          makeDefault
          enabled={interactive}
          target={camera.target}
          enablePan={false}
          minDistance={3}
          maxDistance={34}
          maxPolarAngle={Math.PI / 2.02}
          autoRotate={interactive && camera.motion === "orbit" && !reducedMotion}
          autoRotateSpeed={0.35 + camera.speed * 2}
        />
      </Canvas>

      {showOverlay ? (
        <>
          <div className="pointer-events-none absolute left-4 top-4 z-10 max-w-[62%]">
            <div className="text-[10px] uppercase tracking-[0.24em] text-accent-glow/70">
              {scene.style} · {scene.atmosphere.time_of_day} · {scene.atmosphere.weather}
            </div>
            <h2 className="mt-1 truncate text-sm font-semibold text-foreground/90">{scene.title}</h2>
            <div className="mt-1 text-[10px] text-foreground/40">
              {scene.entities.length} element{scene.entities.length === 1 ? "" : "s"} · v{scene.version} · local
              procedural preview
            </div>
          </div>
          <div className="pointer-events-none absolute right-4 top-4 z-10 flex items-center gap-2">
            <span className="rounded-full border border-white/10 bg-background/65 px-2.5 py-1 text-[9px] uppercase tracking-[0.16em] text-foreground/45 backdrop-blur">
              L1 · behavioral
            </span>
            <span className="rounded-full border border-white/10 bg-background/65 px-2.5 py-1 text-[9px] uppercase tracking-[0.16em] text-foreground/45 backdrop-blur">
              no image model
            </span>
          </div>
          <div className="pointer-events-none absolute bottom-3 left-4 z-10 text-[10px] text-foreground/35">
            Drag to orbit · scroll to zoom · click an element to edit or lock it
          </div>
          {scene.entities.length === 0 && (
            <div className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center">
              <div className="rounded-xl border border-white/10 bg-background/70 px-4 py-3 text-xs text-foreground/55 backdrop-blur">
                This scene has no elements yet. Add one from the inspector.
              </div>
            </div>
          )}
          <div className="pointer-events-none absolute bottom-3 right-4 z-10 text-[10px] text-foreground/30">
            {scene.entities.filter((entity) => entity.role === "subject").map((entity) => entityKindLabel(entity.kind)).join(" · ") ||
              "empty stage"}
          </div>
        </>
      ) : null}
    </div>
  );
}
