"use client";

import { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import type { SceneEntity } from "@/lib/animusStudioApi";
import { attrNumber, entityAccent, entityColor, entityEmissive } from "../sceneUtils";

function Standard({
  color,
  emissive = 0,
  roughness = 0.72,
  metalness = 0.08,
  opacity = 1,
}: {
  color: string;
  emissive?: number;
  roughness?: number;
  metalness?: number;
  opacity?: number;
}) {
  return (
    <meshStandardMaterial
      color={color}
      emissive={emissive > 0 ? color : "#000000"}
      emissiveIntensity={emissive}
      roughness={roughness}
      metalness={metalness}
      transparent={opacity < 1}
      opacity={opacity}
      flatShading
    />
  );
}

export function LibraryBody({ entity }: { entity: SceneEntity }) {
  const color = entityColor(entity);
  const accent = entityAccent(entity);
  const books = Math.max(6, Math.round(attrNumber(entity, "books", 22)));
  return (
    <group>
      <mesh position={[0, 1.2, 0]}>
        <boxGeometry args={[1.55, 2.4, 0.62]} />
        <Standard color={color} roughness={0.88} />
      </mesh>
      {[0.25, 0.72, 1.19, 1.66, 2.13].map((y) => (
        <mesh key={y} position={[0, y, 0.34]}>
          <boxGeometry args={[1.46, 0.035, 0.12]} />
          <Standard color={accent} emissive={0.04} roughness={0.7} />
        </mesh>
      ))}
      {Array.from({ length: Math.min(books, 34) }, (_, index) => {
        const shelf = index % 5;
        const column = Math.floor(index / 5);
        return (
          <mesh
            key={index}
            position={[-0.63 + column * 0.11, 0.33 + shelf * 0.47, 0.43]}
            rotation={[0, 0, index % 7 === 0 ? 0.1 : 0]}
          >
            <boxGeometry args={[0.06, 0.28 + (index % 3) * 0.03, 0.08]} />
            <Standard color={index % 3 === 0 ? accent : entityAccent(entity)} emissive={0.02} />
          </mesh>
        );
      })}
      <mesh position={[0, 2.32, 0.2]}>
        <boxGeometry args={[1.62, 0.08, 0.28]} />
        <Standard color={accent} emissive={0.12} />
      </mesh>
    </group>
  );
}

export function TableBody({ entity }: { entity: SceneEntity }) {
  const color = entityColor(entity);
  return (
    <group>
      <mesh position={[0, 0.08, 0]}>
        <boxGeometry args={[1.3, 0.12, 0.72]} />
        <Standard color={color} roughness={0.66} />
      </mesh>
      {[
        [-0.52, -0.26],
        [0.52, -0.26],
        [-0.52, 0.26],
        [0.52, 0.26],
      ].map(([x, z]) => (
        <mesh key={`${x}-${z}`} position={[x, -0.22, z]}>
          <boxGeometry args={[0.08, 0.5, 0.08]} />
          <Standard color={entityAccent(entity)} roughness={0.8} />
        </mesh>
      ))}
      <mesh position={[0.18, 0.19, 0]} rotation={[0, 0.2, 0]}>
        <boxGeometry args={[0.3, 0.04, 0.22]} />
        <Standard color={entityAccent(entity)} emissive={0.08} />
      </mesh>
    </group>
  );
}

export function LanternBody({ entity }: { entity: SceneEntity }) {
  const color = entityColor(entity);
  const emissive = Math.max(0.6, entityEmissive(entity));
  const suspended = /suspended/i.test(entity.label);
  if (suspended) {
    return (
      <group>
        <mesh position={[0, 0.7, 0]}>
          <cylinderGeometry args={[0.008, 0.008, 1.4, 4]} />
          <meshBasicMaterial color={entityAccent(entity)} transparent opacity={0.35} />
        </mesh>
        <mesh>
          <sphereGeometry args={[0.2, 16, 12]} />
          <meshStandardMaterial
            color={color}
            emissive={color}
            emissiveIntensity={emissive * 2.2}
            roughness={0.24}
            toneMapped={false}
          />
        </mesh>
        <mesh>
          <sphereGeometry args={[0.42, 12, 8]} />
          <meshBasicMaterial color={color} transparent opacity={0.08} depthWrite={false} />
        </mesh>
      </group>
    );
  }
  return (
    <group>
      <mesh position={[0, 0.08, 0]}>
        <cylinderGeometry args={[0.26, 0.34, 0.16, 8]} />
        <Standard color={entityAccent(entity)} roughness={0.88} />
      </mesh>
      <mesh position={[0, 0.72, 0]}>
        <cylinderGeometry args={[0.035, 0.05, 1.28, 6]} />
        <Standard color={entityAccent(entity)} roughness={0.9} metalness={0.2} />
      </mesh>
      <mesh position={[0, 1.46, 0]}>
        <boxGeometry args={[0.34, 0.42, 0.34]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={emissive * 2.2}
          roughness={0.28}
          toneMapped={false}
        />
      </mesh>
      <mesh position={[0, 1.72, 0]}>
        <coneGeometry args={[0.28, 0.16, 4]} />
        <Standard color={entityAccent(entity)} roughness={0.7} metalness={0.3} />
      </mesh>
      <mesh position={[0, 1.46, 0]}>
        <sphereGeometry args={[0.5, 12, 8]} />
        <meshBasicMaterial color={color} transparent opacity={0.07} depthWrite={false} />
      </mesh>
    </group>
  );
}

export function ColumnBody({ entity }: { entity: SceneEntity }) {
  const color = entityColor(entity);
  const accent = entityAccent(entity);
  const variant = attrNumber(entity, "variant", 0);
  const height = Math.max(1.7, 3.2 - variant * 0.4);
  return (
    <group>
      <mesh position={[0, 0.12, 0]}>
        <cylinderGeometry args={[0.46, 0.56, 0.24, 12]} />
        <Standard color={accent} roughness={0.85} />
      </mesh>
      <mesh position={[0, height / 2, 0]}>
        <cylinderGeometry args={[0.24, 0.32, height, 14]} />
        <Standard color={color} roughness={0.82} />
      </mesh>
      <mesh position={[0, height + 0.12, 0]}>
        <cylinderGeometry args={[0.48, 0.32, 0.24, 12]} />
        <Standard color={accent} roughness={0.78} />
      </mesh>
    </group>
  );
}

export function RingBody({ entity }: { entity: SceneEntity }) {
  const color = entityColor(entity);
  const emissive = Math.max(0.3, entityEmissive(entity));
  const ref = useRef<THREE.Group>(null);
  useFrame(({ clock }) => {
    if (ref.current) ref.current.rotation.y = clock.getElapsedTime() * 0.08;
  });
  return (
    <group ref={ref}>
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[1.35, 0.035, 8, 96]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={emissive} metalness={0.4} roughness={0.28} />
      </mesh>
      <mesh rotation={[Math.PI / 2, 0.6, 0]}>
        <torusGeometry args={[1.1, 0.022, 8, 96]} />
        <meshStandardMaterial color={entityAccent(entity)} emissive={entityAccent(entity)} emissiveIntensity={emissive * 0.7} />
      </mesh>
    </group>
  );
}

export function ObservatoryBody({ entity }: { entity: SceneEntity }) {
  const color = entityColor(entity);
  const accent = entityAccent(entity);
  const emissive = Math.max(0.15, entityEmissive(entity));
  return (
    <group>
      <mesh position={[0, 0.35, 0]}>
        <cylinderGeometry args={[1.5, 1.7, 0.7, 24]} />
        <Standard color={color} roughness={0.78} metalness={0.18} />
      </mesh>
      <mesh position={[0, 0.7, 0]}>
        <sphereGeometry args={[1.45, 32, 16, 0, Math.PI * 2, 0, Math.PI / 2]} />
        <Standard color={accent} roughness={0.46} metalness={0.42} opacity={0.92} />
      </mesh>
      <mesh position={[0, 0.7, 0]}>
        <sphereGeometry args={[1.47, 16, 8, 0, Math.PI * 2, 0, Math.PI / 2]} />
        <meshBasicMaterial color={accent} wireframe transparent opacity={0.22} />
      </mesh>
      <mesh position={[0, 1.4, 0]}>
        <cylinderGeometry args={[0.08, 0.12, 1, 8]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={emissive} />
      </mesh>
      <mesh position={[0, 1.92, 0]}>
        <sphereGeometry args={[0.08, 12, 8]} />
        <meshBasicMaterial color={accent} toneMapped={false} />
      </mesh>
    </group>
  );
}

export function MonolithBody({ entity }: { entity: SceneEntity }) {
  const color = entityColor(entity);
  const accent = entityAccent(entity);
  const height = 3 + (entity.transform.scale[1] % 2);
  return (
    <group>
      <mesh position={[0, height / 2, 0]} rotation={[0, 0, 0.03]}>
        <boxGeometry args={[0.7, height, 0.42]} />
        <Standard color={color} roughness={0.58} metalness={0.18} />
      </mesh>
      <mesh position={[0.36, height * 0.55, 0]}>
        <boxGeometry args={[0.018, height * 0.62, 0.02]} />
        <meshBasicMaterial color={accent} toneMapped={false} />
      </mesh>
    </group>
  );
}

export function MoteBody({ entity }: { entity: SceneEntity }) {
  const color = entityColor(entity);
  return (
    <mesh>
      <sphereGeometry args={[0.06, 8, 6]} />
      <meshBasicMaterial color={color} transparent opacity={0.8} toneMapped={false} />
    </mesh>
  );
}

export function FireflyBody({ entity }: { entity: SceneEntity }) {
  const color = entityColor(entity);
  return (
    <group>
      <mesh>
        <sphereGeometry args={[0.045, 8, 6]} />
        <meshBasicMaterial color={color} toneMapped={false} />
      </mesh>
      <mesh>
        <sphereGeometry args={[0.16, 10, 8]} />
        <meshBasicMaterial color={color} transparent opacity={0.12} depthWrite={false} />
      </mesh>
    </group>
  );
}

export function PathBody({ entity }: { entity: SceneEntity }) {
  const color = entityColor(entity);
  const accent = entityAccent(entity);
  return (
    <group>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.012, 0]}>
        <planeGeometry args={[1, 1]} />
        <meshStandardMaterial color={color} roughness={0.94} transparent opacity={0.72} />
      </mesh>
      {[-0.49, 0.49].map((x) => (
        <mesh key={x} position={[x, 0.016, 0]} rotation={[-Math.PI / 2, 0, 0]}>
          <planeGeometry args={[0.012, 1]} />
          <meshBasicMaterial color={accent} transparent opacity={0.35} toneMapped={false} />
        </mesh>
      ))}
    </group>
  );
}

export function ShrineBody({ entity }: { entity: SceneEntity }) {
  const color = entityColor(entity);
  const accent = entityAccent(entity);
  return (
    <group>
      {[0, 1, 2].map((step) => (
        <mesh key={step} position={[0, 0.1 + step * 0.16, 0]}>
          <boxGeometry args={[2.2 - step * 0.3, 0.16, 1.2 - step * 0.14]} />
          <Standard color={color} roughness={0.9} />
        </mesh>
      ))}
      <mesh position={[0, 0.74, 0]}>
        <boxGeometry args={[0.9, 0.16, 0.56]} />
        <Standard color={accent} roughness={0.7} />
      </mesh>
      <mesh position={[0, 1.05, 0]}>
        <torusGeometry args={[0.38, 0.035, 8, 48]} />
        <meshStandardMaterial color={accent} emissive={accent} emissiveIntensity={0.7} />
      </mesh>
    </group>
  );
}

export function ColonnadeBody({ entity }: { entity: SceneEntity }) {
  const color = entityColor(entity);
  const accent = entityAccent(entity);
  return (
    <group>
      {[-1, 0, 1].map((offset) => (
        <group key={offset} position={[offset * 0.85, 0, 0]}>
          <mesh position={[0, 0.08, 0]}>
            <cylinderGeometry args={[0.28, 0.34, 0.16, 10]} />
            <Standard color={accent} roughness={0.8} />
          </mesh>
          <mesh position={[0, 1.25, 0]}>
            <cylinderGeometry args={[0.18, 0.23, 2.4, 12]} />
            <Standard color={color} roughness={0.84} />
          </mesh>
          <mesh position={[0, 2.48, 0]}>
            <boxGeometry args={[0.55, 0.16, 0.55]} />
            <Standard color={accent} roughness={0.7} />
          </mesh>
        </group>
      ))}
    </group>
  );
}
