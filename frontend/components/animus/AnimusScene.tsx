"use client";

import { Suspense, useEffect, useId, useMemo, useRef, useState, useSyncExternalStore, type RefObject } from "react";
import { Html, Line, OrbitControls, PerspectiveCamera, TransformControls } from "@react-three/drei";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";
import type { SceneEntity, SceneGraph, Vec3 } from "@/lib/animusStudioApi";
import type { SceneComparison } from "@/lib/sceneCompare";
import { traceEntities } from "@/lib/sceneCompare";
import EntityMesh from "./EntityMesh";
import SceneBoundary from "./SceneBoundary";
import SceneNavigator from "./SceneNavigator";
import SceneTrace from "./workbench/SceneTrace";
import { entityKindLabel, entitySize, isEntityLocked } from "./sceneUtils";
import { clampPosition, clampScale } from "@/lib/sceneContract";
import { DEFAULT_CAMERA_BOUNDS, resolveCameraMove, type CameraObstacle } from "@/lib/imagine/collision";
import { DEFAULT_LAYERS, type GizmoMode, type StageLayer } from "@/lib/workbenchState";
import { AmbientMotes, PracticalLights, WorldSky, WorldTerrain } from "./world/WorldBackdrop";
import WorldPostFx from "./world/WorldPostFx";
import type { WorldSpec } from "@/lib/imagine/world";

export interface AnimusCameraView {
  position: Vec3;
  target: Vec3;
  fov?: number;
}

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

function subscribeReducedMotion(onChange: () => void): () => void {
  const query = window.matchMedia("(prefers-reduced-motion: reduce)");
  query.addEventListener?.("change", onChange);
  return () => query.removeEventListener?.("change", onChange);
}

function readReducedMotion(): boolean {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function useReducedMotion(): boolean {
  return useSyncExternalStore(subscribeReducedMotion, readReducedMotion, () => false);
}

function subscribeVisibility(onChange: () => void): () => void {
  document.addEventListener("visibilitychange", onChange);
  return () => document.removeEventListener("visibilitychange", onChange);
}

function readVisibility(): boolean {
  return !document.hidden;
}

function usePageVisible(): boolean {
  return useSyncExternalStore(subscribeVisibility, readVisibility, () => true);
}

function TextureSkyDome({ url }: { url: string }) {
  const [texture, setTexture] = useState<THREE.Texture | null>(null);
  useEffect(() => {
    let active = true;
    const loader = new THREE.TextureLoader();
    loader.setCrossOrigin("anonymous");
    loader.load(
      url,
      (loaded) => {
        if (!active) {
          loaded.dispose();
          return;
        }
        loaded.colorSpace = THREE.SRGBColorSpace;
        loaded.wrapS = THREE.RepeatWrapping;
        setTexture(loaded);
      },
      undefined,
      () => {
        if (active) setTexture(null);
      },
    );
    return () => {
      active = false;
    };
  }, [url]);

  useEffect(() => () => texture?.dispose(), [texture]);

  if (!texture) return null;
  return (
    <mesh scale={[90, 90, 90]} renderOrder={-10}>
      <sphereGeometry args={[1, 64, 32]} />
      <meshBasicMaterial map={texture} side={THREE.BackSide} depthWrite={false} toneMapped={false} />
    </mesh>
  );
}

function SkyDome({ scene, textureUrl }: { scene: SceneGraph; textureUrl?: string | null }) {
  const { sky } = scene.atmosphere;
  if (textureUrl) {
    return (
      <Suspense fallback={null}>
        <TextureSkyDome url={textureUrl} />
      </Suspense>
    );
  }
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

function CameraController({ scene, view }: { scene: SceneGraph; view: AnimusCameraView | null }) {
  return (
    <PerspectiveCamera
      makeDefault
      position={view?.position ?? scene.camera.position}
      fov={view?.fov ?? scene.camera.fov}
      near={0.05}
      far={300}
    />
  );
}

function FirstPersonRig({
  scene,
  enabled,
  onExit,
  lookMode = "drag",
  collision = false,
  movementRef,
}: {
  scene: SceneGraph;
  enabled: boolean;
  onExit?: () => void;
  lookMode?: "drag" | "pointer";
  collision?: boolean;
  movementRef?: RefObject<{ x: number; y: number }>;
}) {
  const camera = useThree((state) => state.camera);
  const gl = useThree((state) => state.gl);
  const invalidate = useThree((state) => state.invalidate);
  const yaw = useRef(0);
  const pitch = useRef(0);
  const keys = useRef(new Set<string>());
  const dragging = useRef(false);
  const initialized = useRef(false);
  const pointer = useRef({ x: 0, y: 0 });
  const start = useRef(new THREE.Vector3());
  const move = useRef(new THREE.Vector3());
  const velocity = useRef(new THREE.Vector3());
  const bob = useRef(0);
  const forward = useRef(new THREE.Vector3());
  const right = useRef(new THREE.Vector3());
  const obstacles = useMemo<CameraObstacle[]>(
    () =>
      scene.entities
        .filter(
          (entity) =>
            entity.visible &&
            entity.attributes.collidable?.value !== false &&
            !entity.label.toLowerCase().includes("light"),
        )
        .map((entity) => ({
          x: entity.transform.position[0],
          z: entity.transform.position[2],
          radius: Math.max(0.3, Math.max(entity.transform.scale[0], entity.transform.scale[2]) * 0.45),
        })),
    [scene.entities],
  );

  useEffect(() => {
    if (!enabled) {
      initialized.current = false;
      if (document.pointerLockElement === gl.domElement) document.exitPointerLock();
      return;
    }
    if (initialized.current) return;
    const from = new THREE.Vector3(...scene.camera.position);
    const to = new THREE.Vector3(...scene.camera.target);
    const direction = to.sub(from).normalize();
    yaw.current = Math.atan2(-direction.x, -direction.z);
    pitch.current = Math.asin(Math.max(-1, Math.min(1, direction.y)));
    start.current.copy(from);
    camera.position.copy(from);
    camera.rotation.set(pitch.current, yaw.current, 0, "YXZ");
    camera.updateProjectionMatrix();
    initialized.current = true;
    invalidate();
  }, [camera, enabled, gl.domElement, invalidate, scene]);

  useEffect(() => {
    if (!enabled) return;
    const isEditable = (target: EventTarget | null) => {
      const element = target as HTMLElement | null;
      return Boolean(element?.closest("input, textarea, select, [contenteditable='true']"));
    };
    const pressedKeys = keys.current;
    const onKeyDown = (event: KeyboardEvent) => {
      if (isEditable(event.target)) return;
      if (event.code === "KeyF") {
        event.preventDefault();
        if (document.pointerLockElement === gl.domElement) document.exitPointerLock();
        onExit?.();
        return;
      }
      if (event.code === "KeyR") {
        event.preventDefault();
        camera.position.copy(start.current);
        velocity.current.set(0, 0, 0);
        bob.current = 0;
        const to = new THREE.Vector3(...scene.camera.target);
        const direction = to.sub(start.current).normalize();
        yaw.current = Math.atan2(-direction.x, -direction.z);
        pitch.current = Math.asin(Math.max(-1, Math.min(1, direction.y)));
        invalidate();
        return;
      }
      if (
        [
          "KeyW",
          "KeyA",
          "KeyS",
          "KeyD",
          "ArrowUp",
          "ArrowDown",
          "ArrowLeft",
          "ArrowRight",
          "ShiftLeft",
          "ShiftRight",
        ].includes(event.code)
      ) {
        event.preventDefault();
        pressedKeys.add(event.code);
      }
    };
    const onKeyUp = (event: KeyboardEvent) => {
      pressedKeys.delete(event.code);
    };
    const onPointerDown = (event: PointerEvent) => {
      if (event.button !== 0) return;
      event.preventDefault();
      dragging.current = true;
      pointer.current = { x: event.clientX, y: event.clientY };
      if (lookMode === "pointer" && document.pointerLockElement !== gl.domElement) {
        try {
          const request = gl.domElement.requestPointerLock();
          if (request instanceof Promise) request.catch(() => undefined);
        } catch {
          dragging.current = true;
        }
      }
      if (document.pointerLockElement !== gl.domElement) {
        gl.domElement.setPointerCapture?.(event.pointerId);
      }
    };
    const onPointerMove = (event: PointerEvent) => {
      const locked = document.pointerLockElement === gl.domElement;
      if (!dragging.current && !locked) return;
      const dx = locked ? event.movementX : event.clientX - pointer.current.x;
      const dy = locked ? event.movementY : event.clientY - pointer.current.y;
      pointer.current = { x: event.clientX, y: event.clientY };
      yaw.current -= dx * 0.0032;
      pitch.current = Math.max(-1.2, Math.min(1.2, pitch.current - dy * 0.0028));
    };
    const onPointerUp = (event: PointerEvent) => {
      dragging.current = false;
      gl.domElement.releasePointerCapture?.(event.pointerId);
    };
    const onPointerLockChange = () => {
      if (document.pointerLockElement === gl.domElement) dragging.current = false;
    };
    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("keyup", onKeyUp);
    document.addEventListener("pointerlockchange", onPointerLockChange);
    gl.domElement.addEventListener("pointerdown", onPointerDown);
    gl.domElement.addEventListener("pointermove", onPointerMove);
    gl.domElement.addEventListener("pointerup", onPointerUp);
    gl.domElement.addEventListener("pointercancel", onPointerUp);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("keyup", onKeyUp);
      document.removeEventListener("pointerlockchange", onPointerLockChange);
      gl.domElement.removeEventListener("pointerdown", onPointerDown);
      gl.domElement.removeEventListener("pointermove", onPointerMove);
      gl.domElement.removeEventListener("pointerup", onPointerUp);
      gl.domElement.removeEventListener("pointercancel", onPointerUp);
      pressedKeys.clear();
      dragging.current = false;
      if (document.pointerLockElement === gl.domElement) document.exitPointerLock();
    };
  }, [camera, enabled, gl, invalidate, lookMode, onExit, scene.camera.target]);

  useFrame((_, delta) => {
    if (!enabled) return;
    const speed = keys.current.has("ShiftLeft") || keys.current.has("ShiftRight") ? 8.5 : 4.4;
    move.current.set(0, 0, 0);
    forward.current.set(-Math.sin(yaw.current), 0, -Math.cos(yaw.current));
    right.current.set(Math.cos(yaw.current), 0, -Math.sin(yaw.current));
    if (keys.current.has("KeyW") || keys.current.has("ArrowUp")) move.current.add(forward.current);
    if (keys.current.has("KeyS") || keys.current.has("ArrowDown")) move.current.sub(forward.current);
    if (keys.current.has("KeyD") || keys.current.has("ArrowRight")) move.current.add(right.current);
    if (keys.current.has("KeyA") || keys.current.has("ArrowLeft")) move.current.sub(right.current);
    const touch = movementRef?.current;
    if (touch) {
      move.current.addScaledVector(forward.current, touch.y);
      move.current.addScaledVector(right.current, touch.x);
    }
    if (move.current.lengthSq() > 1) move.current.normalize();
    const desired = move.current.multiplyScalar(speed);
    velocity.current.lerp(desired, 1 - Math.exp(-9 * Math.min(delta, 0.08)));
    move.current.copy(velocity.current).multiplyScalar(Math.min(delta, 0.08));
    const moving = velocity.current.length() > 0.12;
    if (moving) {
      bob.current += delta * velocity.current.length() * 1.35;
      if (collision) {
        const next = resolveCameraMove(
          camera.position.toArray() as [number, number, number],
          move.current.toArray() as [number, number, number],
          obstacles,
          DEFAULT_CAMERA_BOUNDS,
        );
        camera.position.set(next[0], camera.position.y, next[2]);
      } else {
        camera.position.add(move.current);
      }
    } else {
      velocity.current.multiplyScalar(0.85);
    }
    const eye = scene.camera.position[1];
    const bobOffset = moving ? Math.sin(bob.current * 2.1) * 0.016 : 0;
    const nextY = camera.position.y + (eye + bobOffset - camera.position.y) * Math.min(1, delta * 10);
    camera.position.set(
      Math.max(DEFAULT_CAMERA_BOUNDS.minX, Math.min(DEFAULT_CAMERA_BOUNDS.maxX, camera.position.x)),
      Math.max(0.65, Math.min(2.2, nextY)),
      Math.max(DEFAULT_CAMERA_BOUNDS.minZ, Math.min(DEFAULT_CAMERA_BOUNDS.maxZ, camera.position.z)),
    );
    camera.rotation.set(pitch.current, yaw.current, 0, "YXZ");
    invalidate();
  });

  return null;
}

function CameraRig({
  scene,
  preset,
  focus,
  view,
}: {
  scene: SceneGraph;
  preset: string | null;
  focus: [number, number, number] | null;
  view: AnimusCameraView | null;
}) {
  const camera = useThree((state) => state.camera);
  const invalidate = useThree((state) => state.invalidate);
  const target = useMemo(() => new THREE.Vector3(...scene.camera.target), [scene.camera.target]);
  useEffect(() => {
    if (view) {
      camera.position.set(...view.position);
      camera.lookAt(...view.target);
      camera.updateProjectionMatrix();
      invalidate();
      return;
    }
    if (!preset) return;
    const radius = Math.max(
      7,
      Math.min(
        24,
        Math.hypot(
          scene.camera.position[0] - target.x,
          scene.camera.position[1] - target.y,
          scene.camera.position[2] - target.z,
        ) || 12,
      ),
    );
    const focusPoint = focus ? new THREE.Vector3(...focus) : target;
    if (preset === "top") camera.position.set(focusPoint.x, focusPoint.y + radius * 1.7, focusPoint.z + 0.01);
    else if (preset === "eye")
      camera.position.set(focusPoint.x, focusPoint.y + radius * 0.18, focusPoint.z + radius * 1.45);
    else if (preset === "detail")
      camera.position.set(focusPoint.x + radius * 0.4, focusPoint.y + radius * 0.22, focusPoint.z + radius * 0.62);
    else if (preset === "wide")
      camera.position.set(focusPoint.x + radius * 1.35, focusPoint.y + radius * 0.95, focusPoint.z + radius * 1.35);
    else camera.position.set(...scene.camera.position);
    camera.lookAt(focusPoint);
    camera.updateProjectionMatrix();
    invalidate();
  }, [camera, focus, invalidate, preset, scene.camera.position, target, view]);
  return null;
}

function relationColor(relation: string): string {
  if (relation === "above") return "#e8b45a";
  if (relation === "below") return "#c7855a";
  if (relation === "behind") return "#7f8ba8";
  if (relation === "in_front_of") return "#9fd8c8";
  if (relation === "around") return "#b595d6";
  return "#6fe3c4";
}

function RelationLayer({
  scene,
  showLabels,
}: {
  scene: SceneGraph;
  showLabels: boolean;
}) {
  const byId = useMemo(() => new Map(scene.entities.map((entity) => [entity.id, entity])), [scene.entities]);
  const visible = scene.relations.slice(0, 80);
  return (
    <group>
      {visible.map((relation, index) => {
        const from = byId.get(relation.subject_id);
        const to = byId.get(relation.object_id);
        if (!from || !to) return null;
        const start: [number, number, number] = [
          from.transform.position[0],
          from.transform.position[1] + 0.38,
          from.transform.position[2],
        ];
        const end: [number, number, number] = [
          to.transform.position[0],
          to.transform.position[1] + 0.38,
          to.transform.position[2],
        ];
        const mid: [number, number, number] = [(start[0] + end[0]) / 2, (start[1] + end[1]) / 2 + 0.2, (start[2] + end[2]) / 2];
        return (
          <group key={`${relation.subject_id}-${relation.relation}-${relation.object_id}-${index}`}>
            <Line
              points={[start, end]}
              color={relationColor(relation.relation)}
              lineWidth={1}
              dashed
              dashSize={0.28}
              gapSize={0.18}
              transparent
              opacity={0.6}
            />
            {showLabels && visible.length <= 16 ? (
              <Html position={mid} center distanceFactor={14} zIndexRange={[12, 0]}>
                <span className="pointer-events-none whitespace-nowrap rounded-full border border-white/15 bg-[#07080a]/85 px-1.5 py-0.5 font-mono text-[11px] uppercase tracking-[0.12em] text-foreground/55 backdrop-blur">
                  {relation.relation.replace(/_/g, " ")}
                </span>
              </Html>
            ) : null}
          </group>
        );
      })}
    </group>
  );
}

function round(value: number, precision = 6): number {
  const factor = 10 ** precision;
  return Math.round(value * factor) / factor;
}

function SceneEntityNode({
  entity,
  scene,
  selected,
  onSelect,
  animate,
  gizmoMode,
  canTransform,
  showGizmo,
  showLocks,
  showProvenance,
  changeState,
  onDragStateChange,
  onTransform,
}: {
  entity: SceneEntity;
  scene: SceneGraph;
  selected: boolean;
  onSelect: (entityId: string) => void;
  animate: boolean;
  gizmoMode: GizmoMode;
  canTransform: boolean;
  showGizmo: boolean;
  showLocks: boolean;
  showProvenance: boolean;
  changeState: "added" | "changed" | null;
  onDragStateChange: (dragging: boolean) => void;
  onTransform?: (next: {
    entityId: string;
    position: [number, number, number];
    rotation: [number, number, number];
    scale: [number, number, number];
  }) => Promise<boolean>;
}) {
  const rootRef = useRef<THREE.Group>(null);
  const startRef = useRef<{ position: THREE.Vector3; rotation: THREE.Euler; scale: THREE.Vector3 } | null>(null);
  const size = entitySize(entity);

  const begin = () => {
    if (!rootRef.current) return;
    startRef.current = {
      position: rootRef.current.position.clone(),
      rotation: rootRef.current.rotation.clone(),
      scale: rootRef.current.scale.clone(),
    };
    onDragStateChange(true);
  };

  const finish = async () => {
    onDragStateChange(false);
    const root = rootRef.current;
    const start = startRef.current;
    startRef.current = null;
    if (!root || !start || !onTransform) return;
    const next = {
      entityId: entity.id,
      position: [
        round(clampPosition(root.position.x)),
        round(clampPosition(root.position.y)),
        round(clampPosition(root.position.z)),
      ] as [number, number, number],
      rotation: [round(root.rotation.x), round(root.rotation.y), round(root.rotation.z)] as [number, number, number],
      scale: [
        round(clampScale(root.scale.x / size)),
        round(clampScale(root.scale.y / size)),
        round(clampScale(root.scale.z / size)),
      ] as [number, number, number],
    };
    const changed =
      next.position.some((value, index) => Math.abs(value - entity.transform.position[index]) > 0.0001) ||
      next.rotation.some((value, index) => Math.abs(value - entity.transform.rotation[index]) > 0.0001) ||
      next.scale.some((value, index) => Math.abs(value - entity.transform.scale[index]) > 0.0001);
    if (!changed) return;
    const applied = await onTransform(next);
    if (!applied) {
      root.position.copy(start.position);
      root.rotation.copy(start.rotation);
      root.scale.copy(start.scale);
    }
  };

  return (
    <>
      <EntityMesh
        entity={entity}
        scene={scene}
        selected={selected}
        onSelect={onSelect}
        animate={animate}
        groupRef={rootRef}
        showLockRing={showLocks}
        showProvenance={showProvenance}
        changeState={changeState}
      />
      {selected && showGizmo && canTransform ? (
        <TransformControls
          object={rootRef as unknown as RefObject<THREE.Object3D>}
          mode={gizmoMode}
          size={0.72}
          space="world"
          translationSnap={0.1}
          rotationSnap={Math.PI / 36}
          scaleSnap={0.05}
          onMouseDown={begin}
          onMouseUp={() => {
            void finish();
          }}
        />
      ) : null}
    </>
  );
}

export default function AnimusScene({
  scene,
  selectedId,
  onSelect,
  className = "",
  showOverlay = true,
  interactive = true,
  layers = DEFAULT_LAYERS,
  gizmoMode = "translate",
  readOnly = false,
  cameraPreset = null,
  cameraView = null,
  diff = null,
  traceScene = null,
  visibleIds = null,
  animate = true,
  frameloop = "always",
  dpr = [1, 1.7],
  cameraMode = "orbit",
  description,
  onCameraInteract,
  onTransform,
  onExitFirstPerson,
  firstPersonLookMode = "drag",
  collisionEnabled = false,
  movementRef,
  environmentTextureUrl = null,
}: {
  scene: SceneGraph;
  selectedId: string | null;
  onSelect: (entityId: string | null) => void;
  className?: string;
  showOverlay?: boolean;
  interactive?: boolean;
  layers?: Record<StageLayer, boolean>;
  gizmoMode?: GizmoMode;
  readOnly?: boolean;
  cameraPreset?: string | null;
  cameraView?: AnimusCameraView | null;
  diff?: SceneComparison | null;
  traceScene?: SceneGraph | null;
  visibleIds?: Set<string> | null;
  animate?: boolean;
  frameloop?: "always" | "demand";
  dpr?: number | [number, number];
  cameraMode?: "orbit" | "firstPerson";
  description?: string;
  onCameraInteract?: () => void;
  onExitFirstPerson?: () => void;
  firstPersonLookMode?: "drag" | "pointer";
  collisionEnabled?: boolean;
  movementRef?: RefObject<{ x: number; y: number }>;
  environmentTextureUrl?: string | null;
  onTransform?: (next: {
    entityId: string;
    position: [number, number, number];
    rotation: [number, number, number];
    scale: [number, number, number];
  }) => Promise<boolean>;
}) {
  const camera = scene.camera;
  const world = (scene.metadata.world as WorldSpec | undefined) ?? null;
  const reducedMotion = useReducedMotion();
  const pageVisible = usePageVisible();
  const descriptionId = useId();
  const [dragging, setDragging] = useState(false);
  const [contextLost, setContextLost] = useState(false);
  const [sceneNonce, setSceneNonce] = useState(0);
  const selected = scene.entities.find((entity) => entity.id === selectedId) ?? null;
  const renderEntities = useMemo(
    () => (visibleIds ? scene.entities.filter((entity) => visibleIds.has(entity.id)) : scene.entities),
    [scene.entities, visibleIds],
  );
  const entityLabels = renderEntities.map((entity) => `${entity.label} (${entityKindLabel(entity.kind)})`);
  const addedIds = useMemo(() => new Set(diff?.added.map((item) => item.entity_id) ?? []), [diff]);
  const changedIds = useMemo(() => new Set(diff?.changed.map((item) => item.entity_id) ?? []), [diff]);
  const traceSet = useMemo(
    () => (traceScene && diff ? traceEntities(traceScene, scene, diff, 16) : null),
    [diff, scene, traceScene],
  );
  return (
    <div
      role="region"
      aria-label={interactive ? "Interactive 3D scene preview" : "3D scene preview"}
      aria-describedby={descriptionId}
      className={`relative overflow-hidden bg-[#050711] ${className}`}
      data-testid="animus-scene"
    >
      <p id={descriptionId} className="sr-only" aria-live="polite">
        {description ??
          (showOverlay
            ? `${scene.title}, ${scene.style} style, ${scene.atmosphere.time_of_day}, ${scene.atmosphere.weather}. ${
                entityLabels.length ? `Elements: ${entityLabels.join(", ")}.` : "The scene has no elements yet."
              } ${
                cameraMode === "firstPerson"
                  ? "First-person view. Use W A S D to move, drag to look, and F to return to orbit."
                  : "Drag to orbit, scroll to zoom, and select an element to edit it."
              } ${selected ? `${selected.label} is selected.` : ""}`
            : "Scene preview. Visual details are intentionally not described.")}
        {diff && traceScene
          ? ` Comparison with the live head: ${diff.added.length} added, ${diff.changed.length} changed, ${diff.removed.length} removed. ${
              traceSet?.shown ? `${traceSet.shown} previous positions are drawn as trace.` : ""
            }`
          : ""}
      </p>
      <SceneBoundary scene={scene}>
        <Canvas
          key={sceneNonce}
          dpr={Array.isArray(dpr) ? [1, Math.min(1.5, dpr[1])] : Math.min(1.5, dpr)}
          frameloop={contextLost || !pageVisible ? "demand" : frameloop}
          style={{ touchAction: cameraMode === "firstPerson" ? "none" : "auto" }}
          gl={{ antialias: true, powerPreference: "high-performance", preserveDrawingBuffer: true }}
          onCreated={({ gl }) => {
            const canvas = gl.domElement;
            canvas.addEventListener("webglcontextlost", (event) => {
              event.preventDefault();
              setContextLost(true);
            });
            canvas.addEventListener("webglcontextrestored", () => setContextLost(false));
          }}
          onPointerMissed={() => {
            if (!dragging) onSelect(null);
          }}
        >
          <CameraController scene={scene} view={cameraView} />
          <FirstPersonRig
            scene={scene}
            enabled={cameraMode === "firstPerson"}
            onExit={onExitFirstPerson}
            lookMode={firstPersonLookMode}
            collision={collisionEnabled}
            movementRef={movementRef}
          />
          {cameraMode === "orbit" ? (
            <CameraRig
              scene={scene}
              preset={cameraPreset}
              focus={selected?.transform.position ?? null}
              view={cameraView}
            />
          ) : null}
          <fogExp2 attach="fog" args={[scene.atmosphere.fog.color, Math.min(0.09, scene.atmosphere.fog.density * 2.4)]} />
          {world && !environmentTextureUrl ? (
            <WorldSky scene={scene} world={world} />
          ) : (
            <SkyDome scene={scene} textureUrl={environmentTextureUrl} />
          )}
          {environmentTextureUrl ? null : <SkyStars scene={scene} />}
          <SceneLights scene={scene} />
          {world ? <PracticalLights scene={scene} world={world} /> : null}
          {world ? <WorldTerrain world={world} /> : <Ground scene={scene} />}
          {world ? <AmbientMotes scene={scene} world={world} animate={animate && !reducedMotion} /> : null}
          {layers.grid ? (
            <gridHelper args={[48, 48, "#4b5b57", "#222b29"]} position={[0, 0.005, 0]} />
          ) : null}
          {layers.relations ? <RelationLayer scene={scene} showLabels={layers.labels} /> : null}
          {layers.changes && traceSet ? <SceneTrace traces={traceSet} /> : null}
          {renderEntities.map((entity) => (
            <SceneEntityNode
              key={entity.id}
              entity={entity}
              scene={scene}
              selected={selectedId === entity.id}
              onSelect={onSelect}
              animate={animate && !reducedMotion}
              gizmoMode={gizmoMode}
              canTransform={interactive && !readOnly && !isEntityLocked(entity)}
              showGizmo={interactive && !readOnly}
              showLocks={layers.locks}
              showProvenance={layers.provenance}
              changeState={
                layers.changes ? (addedIds.has(entity.id) ? "added" : changedIds.has(entity.id) ? "changed" : null) : null
              }
              onDragStateChange={setDragging}
              onTransform={onTransform}
            />
          ))}
          <Weather scene={scene} animate={animate && !reducedMotion} />
          {world && !reducedMotion ? <WorldPostFx strength={0.28 + world.emissiveBudget * 0.34} /> : null}
          {cameraMode === "orbit" ? (
            <OrbitControls
              makeDefault
              enabled={interactive && !dragging}
              target={cameraView?.target ?? camera.target}
              enablePan={false}
              minDistance={3}
              maxDistance={34}
              maxPolarAngle={Math.PI / 2.02}
              autoRotate={interactive && camera.motion === "orbit" && !reducedMotion}
              autoRotateSpeed={0.35 + camera.speed * 2}
              onStart={() => onCameraInteract?.()}
            />
          ) : null}
        </Canvas>
        {contextLost ? (
          <div className="absolute inset-0 z-20 flex items-center justify-center bg-background/85 p-4 backdrop-blur-sm">
            <div role="alert" className="max-w-sm rounded-xl border border-lock/35 bg-lock/[0.06] p-4 text-center">
              <p className="text-sm font-medium text-lock">The 3D context was lost</p>
              <p className="mt-1 text-[11px] leading-5 text-foreground/50">
                The browser or GPU reset the WebGL context. Your scene data is unchanged.
              </p>
              <button
                type="button"
                onClick={() => {
                  setContextLost(false);
                  setSceneNonce((value) => value + 1);
                }}
                className="mt-3 inline-flex min-h-11 items-center rounded-lg border border-lock/40 bg-lock/[0.08] px-4 text-sm text-lock hover:bg-lock/[0.14]"
              >
                Recover scene
              </button>
            </div>
          </div>
        ) : null}
      </SceneBoundary>

      {showOverlay ? (
        <>
          <div className="pointer-events-none absolute left-4 top-4 z-10 max-w-[62%]">
            <div className="font-mono text-[11px] uppercase tracking-[0.24em] text-signal/70">
              {scene.style} · {scene.atmosphere.time_of_day} · {scene.atmosphere.weather}
            </div>
            <h2 className="mt-1 truncate font-display text-base text-foreground/90">{scene.title}</h2>
            <div className="mt-1 font-mono text-[11px] text-foreground/40">
              {renderEntities.length} element{renderEntities.length === 1 ? "" : "s"} · v{scene.version} · symbolic
              scene graph
            </div>
          </div>
          <div className="pointer-events-none absolute right-4 top-4 z-10 flex items-center gap-2">
            <span className="rounded-full border border-white/10 bg-background/65 px-2.5 py-1 font-mono text-[11px] uppercase tracking-[0.16em] text-foreground/45 backdrop-blur">
              L1 · behavioral
            </span>
            <span className="rounded-full border border-white/10 bg-background/65 px-2.5 py-1 font-mono text-[11px] uppercase tracking-[0.16em] text-foreground/45 backdrop-blur">
              no image model
            </span>
          </div>
          <div className="pointer-events-none absolute bottom-3 left-4 z-10 font-mono text-[11px] text-foreground/35">
            {readOnly ? "Preview is read-only · return to head to edit" : "Drag to orbit · scroll to zoom · click to edit or lock"}
          </div>
          {((layers.changes && diff) || layers.provenance) && (
            <div
              data-testid="scene-lens-legend"
              className="pointer-events-none absolute bottom-3 right-4 z-10 hidden max-w-[285px] rounded-lg border border-white/10 bg-background/80 px-2.5 py-2 backdrop-blur sm:block"
            >
              <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-foreground/35">Scene lens</p>
              {layers.changes && diff ? (
                <div className="mt-1.5 flex items-center gap-2 font-mono text-[11px]">
                  <span className="text-signal">+{diff.added.length} added</span>
                  <span className="text-lock">~{diff.changed.length} changed</span>
                  <span className="text-red-300/80">−{diff.removed.length} removed</span>
                </div>
              ) : null}
              {layers.changes && diff ? (
                <p className="mt-1 font-mono text-[11px] text-foreground/30">solid = added · dashed = changed</p>
              ) : null}
              {layers.changes && traceSet?.shown ? (
                <p data-testid="trace-legend" className="mt-1 font-mono text-[11px] text-foreground/35">
                  trace: {traceSet.shown}
                  {traceSet.omitted ? ` of ${traceSet.total}` : ""} previous position{traceSet.shown === 1 ? "" : "s"}
                </p>
              ) : null}
              {layers.provenance ? (
                <div className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1 font-mono text-[11px] text-foreground/35">
                  <span className="inline-flex items-center gap-1">
                    <span className="h-1.5 w-1.5 rounded-full bg-signal" /> explicit
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <span className="h-1.5 w-1.5 rounded-full bg-[#9fe8d2]" /> implied
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <span className="h-1.5 w-1.5 rounded-full bg-lock" /> candidate
                  </span>
                </div>
              ) : null}
            </div>
          )}
          {renderEntities.length === 0 && (
            <div className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center">
              <div className="rounded-xl border border-white/10 bg-background/70 px-4 py-3 text-xs text-foreground/55 backdrop-blur">
                This scene has no elements yet. Add one from the inspector.
              </div>
            </div>
          )}
          {showOverlay && interactive && (
            <SceneNavigator scene={scene} selectedId={selectedId} onSelect={onSelect} />
          )}
        </>
      ) : null}
    </div>
  );
}
