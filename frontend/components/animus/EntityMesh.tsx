"use client";

import { useMemo, useRef } from "react";
import { Html } from "@react-three/drei";
import { useFrame, type ThreeEvent } from "@react-three/fiber";
import * as THREE from "three";
import type { SceneEntity, SceneGraph } from "@/lib/animusStudioApi";
import {
  attrNumber,
  entityAccent,
  entityColor,
  entityEmissive,
  entityOpacity,
  entitySize,
  isLocked,
} from "./sceneUtils";

interface SurfaceProps {
  color: string;
  roughness?: number;
  metalness?: number;
  emissive?: number;
  opacity?: number;
  side?: THREE.Side;
  wireframe?: boolean;
}

function Surface({
  color,
  roughness = 0.7,
  metalness = 0.05,
  emissive = 0,
  opacity = 1,
  side,
  wireframe = false,
}: SurfaceProps) {
  return (
    <meshStandardMaterial
      color={color}
      roughness={roughness}
      metalness={metalness}
      emissive={emissive > 0 ? color : "#000000"}
      emissiveIntensity={emissive}
      transparent={opacity < 1}
      opacity={opacity}
      side={side}
      wireframe={wireframe}
      flatShading
    />
  );
}

function CastleBody({ entity, style }: { entity: SceneEntity; style: string }) {
  const color = entityColor(entity);
  const accent = entityAccent(entity);
  const windows = Math.round(attrNumber(entity, "windows", 12));
  const gothic = style === "gothic";
  const towerHeight = gothic ? 3.6 : 2.8;
  return (
    <group>
      <mesh position={[0, 0.55, 0]}>
        <boxGeometry args={[3.4, 1.1, 2.2]} />
        <Surface color={color} roughness={0.86} />
      </mesh>
      {[-1.25, 1.25].map((x) =>
        [-0.75, 0.75].map((z) => (
          <group key={`${x}-${z}`} position={[x, 1.35, z]}>
            <mesh>
              <cylinderGeometry args={[0.5, 0.6, towerHeight, 10]} />
              <Surface color={accent} roughness={0.82} />
            </mesh>
            <mesh position={[0, towerHeight / 2 + 0.75, 0]}>
              <coneGeometry args={[0.72, 1.5, 10]} />
              <Surface color={gothic ? "#1a1830" : "#41506a"} roughness={0.6} metalness={0.2} />
            </mesh>
          </group>
        )),
      )}
      <group position={[0, 2.1, 0]}>
        <mesh>
          <cylinderGeometry args={[0.68, 0.82, 3.6, 12]} />
          <Surface color={color} roughness={0.78} />
        </mesh>
        <mesh position={[0, 2.25, 0]}>
          <coneGeometry args={[0.95, 2.3, 12]} />
          <Surface color={gothic ? "#221f3d" : "#50627f"} roughness={0.55} metalness={0.25} />
        </mesh>
      </group>
      <mesh position={[0, 0.62, 1.12]}>
        <boxGeometry args={[0.7, 0.95, 0.12]} />
        <Surface color="#111420" roughness={0.6} />
      </mesh>
      {Array.from({ length: Math.min(windows, 24) }, (_, index) => {
        const column = index % 4;
        const row = Math.floor(index / 4);
        return (
          <mesh key={index} position={[-1.1 + column * 0.72, 0.72 + row * 0.36, 1.1]}>
            <boxGeometry args={[0.16, 0.24, 0.05]} />
            <meshStandardMaterial color="#ffd27a" emissive="#ffb84d" emissiveIntensity={1.7} />
          </mesh>
        );
      })}
    </group>
  );
}

function TreeBody({ entity, forest = false }: { entity: SceneEntity; forest?: boolean }) {
  const leaf = entityColor(entity);
  const trunk = entityAccent(entity);
  const count = forest ? 5 : 1;
  return (
    <group>
      {Array.from({ length: count }, (_, index) => {
        const angle = (index / count) * Math.PI * 2;
        const radius = forest ? 1.4 + (index % 2) * 0.5 : 0;
        const height = forest ? 1.8 + (index % 3) * 0.45 : 2.4;
        return (
          <group key={index} position={[Math.cos(angle) * radius, 0, Math.sin(angle) * radius]}>
            <mesh position={[0, height * 0.28, 0]}>
              <cylinderGeometry args={[0.1, 0.16, height * 0.6, 7]} />
              <Surface color={trunk} roughness={0.95} />
            </mesh>
            {[0, 1, 2].map((layer) => (
              <mesh key={layer} position={[0, height * 0.55 + layer * 0.42, 0]}>
                <coneGeometry args={[0.78 - layer * 0.16, height * 0.72, 8]} />
                <Surface color={leaf} roughness={0.9} />
              </mesh>
            ))}
          </group>
        );
      })}
    </group>
  );
}

function MountainBody({ entity }: { entity: SceneEntity }) {
  const color = entityColor(entity);
  const snow = entityAccent(entity);
  return (
    <group>
      <mesh position={[-0.8, 1.5, 0]}>
        <coneGeometry args={[2.2, 3.2, 5]} />
        <Surface color={color} roughness={1} />
      </mesh>
      <mesh position={[1.5, 0.9, -0.8]}>
        <coneGeometry args={[1.4, 2.1, 5]} />
        <Surface color={color} roughness={1} />
      </mesh>
      <mesh position={[-0.8, 2.55, 0]}>
        <coneGeometry args={[0.7, 0.85, 5]} />
        <Surface color={snow} roughness={0.7} />
      </mesh>
    </group>
  );
}

function WaterBody({ entity }: { entity: SceneEntity }) {
  const color = entityColor(entity);
  const accent = entityAccent(entity);
  const opacity = Math.max(0.45, entityOpacity(entity) * 0.9);
  return (
    <group position={[0, 0.02, 0]}>
      <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <planeGeometry args={[46, 34, 1, 1]} />
        <meshStandardMaterial
          color={color}
          roughness={0.16}
          metalness={0.55}
          transparent
          opacity={opacity}
          envMapIntensity={0.4}
        />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.01, 0]}>
        <planeGeometry args={[46, 34]} />
        <meshBasicMaterial color={accent} transparent opacity={0.06} depthWrite={false} />
      </mesh>
    </group>
  );
}

function FogBody({ entity }: { entity: SceneEntity }) {
  const color = entityColor(entity);
  const opacity = Math.max(0.06, entityOpacity(entity) * 0.4);
  return (
    <group>
      {[0, 1, 2].map((index) => (
        <mesh key={index} position={[0, 0.6 + index * 0.9, -index * 1.2]} rotation={[0, 0, 0]}>
          <planeGeometry args={[10 + index * 2, 4.5]} />
          <meshBasicMaterial
            color={color}
            transparent
            opacity={opacity / (1 + index * 0.4)}
            depthWrite={false}
            side={THREE.DoubleSide}
          />
        </mesh>
      ))}
    </group>
  );
}

function CloudBody({ entity }: { entity: SceneEntity }) {
  const color = entityColor(entity);
  const opacity = Math.max(0.3, entityOpacity(entity));
  return (
    <group>
      {[
        [0, 0, 0, 1.1],
        [0.9, 0.15, 0.2, 0.8],
        [-0.9, -0.1, -0.1, 0.72],
        [0.2, 0.45, -0.3, 0.65],
      ].map(([x, y, z, radius], index) => (
        <mesh key={index} position={[x, y, z]}>
          <sphereGeometry args={[radius, 14, 10]} />
          <meshStandardMaterial color={color} transparent opacity={opacity} roughness={1} />
        </mesh>
      ))}
    </group>
  );
}

function StarBody({ entity }: { entity: SceneEntity }) {
  const count = Math.max(4, Math.round(attrNumber(entity, "count", 12)));
  const color = entityColor(entity);
  const positions = useMemo(() => {
    const values = new Float32Array(count * 3);
    for (let index = 0; index < count; index += 1) {
      const angle = index * 2.399;
      const radius = 1.4 + (index % 4) * 0.35;
      values[index * 3] = Math.cos(angle) * radius;
      values[index * 3 + 1] = Math.sin(angle * 1.7) * radius;
      values[index * 3 + 2] = Math.sin(angle) * radius;
    }
    return values;
  }, [count]);
  return (
    <points>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial color={color} size={0.12} sizeAttenuation transparent opacity={0.95} />
    </points>
  );
}

function FireBody({ entity, animate }: { entity: SceneEntity; animate: boolean }) {
  const color = entityColor(entity);
  const accent = entityAccent(entity);
  const group = useRef<THREE.Group>(null);
  useFrame(({ clock }) => {
    if (!group.current || !animate) return;
    const t = clock.getElapsedTime();
    group.current.scale.y = 1 + Math.sin(t * 7.5) * 0.08;
    group.current.rotation.y = t * 0.35;
  });
  return (
    <group ref={group}>
      {[0, 1, 2].map((index) => (
        <mesh key={index} position={[index * 0.18 - 0.18, 0.55 + index * 0.28, 0]}>
          <coneGeometry args={[0.5 - index * 0.1, 1.3, 7]} />
          <meshStandardMaterial
            color={index === 0 ? color : accent}
            emissive={index === 0 ? color : accent}
            emissiveIntensity={2.4}
            transparent
            opacity={0.82}
          />
        </mesh>
      ))}
      <pointLight color={color} intensity={2.2} distance={7} position={[0, 1, 0]} />
    </group>
  );
}

function PersonBody({ entity }: { entity: SceneEntity }) {
  const color = entityColor(entity);
  const accent = entityAccent(entity);
  return (
    <group>
      <mesh position={[0, 0.9, 0]}>
        <capsuleGeometry args={[0.24, 0.9, 4, 10]} />
        <Surface color={accent} roughness={0.8} />
      </mesh>
      <mesh position={[0, 1.7, 0]}>
        <sphereGeometry args={[0.22, 16, 12]} />
        <Surface color={color} roughness={0.65} />
      </mesh>
      <mesh position={[0, 1.05, 0]}>
        <coneGeometry args={[0.46, 1.4, 8]} />
        <Surface color={accent} roughness={0.9} />
      </mesh>
    </group>
  );
}

function CreatureBody({ entity }: { entity: SceneEntity }) {
  const color = entityColor(entity);
  const accent = entityAccent(entity);
  const wings = Math.round(attrNumber(entity, "wings", 0));
  return (
    <group>
      <mesh position={[0, 0.7, 0]} rotation={[0, 0, Math.PI / 2]}>
        <capsuleGeometry args={[0.32, 1.2, 4, 10]} />
        <Surface color={color} roughness={0.8} />
      </mesh>
      <mesh position={[0.75, 0.95, 0]}>
        <sphereGeometry args={[0.3, 14, 10]} />
        <Surface color={accent} roughness={0.6} />
      </mesh>
      {[-0.45, 0.45].map((z) => (
        <mesh key={z} position={[-0.6, 0.3, z]} rotation={[0, 0, 0.5]}>
          <cylinderGeometry args={[0.07, 0.09, 0.6, 6]} />
          <Surface color={accent} roughness={0.9} />
        </mesh>
      ))}
      {Array.from({ length: Math.min(wings, 6) }, (_, index) => (
        <mesh key={index} position={[0.1, 1.2, (index % 2 === 0 ? 1 : -1) * 0.7]} rotation={[0, 0, -0.5]}>
          <coneGeometry args={[0.5, 1.2, 4]} />
          <Surface color={accent} roughness={0.7} opacity={0.82} />
        </mesh>
      ))}
    </group>
  );
}

function DragonBody({ entity }: { entity: SceneEntity }) {
  const color = entityColor(entity);
  const accent = entityAccent(entity);
  const wings = Math.max(1, Math.round(attrNumber(entity, "wings", 2)));
  return (
    <group>
      <mesh position={[0, 0.8, 0]} rotation={[0, 0, Math.PI / 2]}>
        <capsuleGeometry args={[0.34, 1.7, 4, 12]} />
        <Surface color={color} roughness={0.72} />
      </mesh>
      <mesh position={[1.0, 1.15, 0]} rotation={[0, 0, -0.5]}>
        <cylinderGeometry args={[0.16, 0.24, 0.9, 8]} />
        <Surface color={color} roughness={0.7} />
      </mesh>
      <mesh position={[1.35, 1.35, 0]}>
        <sphereGeometry args={[0.28, 14, 10]} />
        <Surface color={accent} roughness={0.55} metalness={0.2} />
      </mesh>
      {Array.from({ length: Math.min(wings, 4) }, (_, index) => (
        <mesh
          key={index}
          position={[0.2, 1.35, (index % 2 === 0 ? 1 : -1) * 0.9]}
          rotation={[0, 0, -0.65]}
        >
          <coneGeometry args={[0.9, 1.8, 4]} />
          <Surface color={accent} roughness={0.6} opacity={0.7} />
        </mesh>
      ))}
      <mesh position={[-1.35, 0.55, 0]} rotation={[0, 0, 0.5]}>
        <coneGeometry args={[0.18, 1.5, 6]} />
        <Surface color={color} roughness={0.8} />
      </mesh>
    </group>
  );
}

function BuildingBody({ entity }: { entity: SceneEntity }) {
  const color = entityColor(entity);
  const windows = Math.round(attrNumber(entity, "windows", 18));
  return (
    <group>
      <mesh position={[0, 1.5, 0]}>
        <boxGeometry args={[1.8, 3, 1.5]} />
        <Surface color={color} roughness={0.82} />
      </mesh>
      <mesh position={[0, 3.2, 0]}>
        <boxGeometry args={[2, 0.35, 1.7]} />
        <Surface color={entityAccent(entity)} roughness={0.7} />
      </mesh>
      {Array.from({ length: Math.min(windows, 30) }, (_, index) => {
        const column = index % 4;
        const row = Math.floor(index / 4);
        return (
          <mesh key={index} position={[-0.6 + column * 0.4, 0.6 + row * 0.34, 0.78]}>
            <boxGeometry args={[0.16, 0.2, 0.04]} />
            <meshStandardMaterial color="#ffd27a" emissive="#ffb84d" emissiveIntensity={1.5} />
          </mesh>
        );
      })}
    </group>
  );
}

function BoatBody({ entity }: { entity: SceneEntity }) {
  const color = entityColor(entity);
  const accent = entityAccent(entity);
  return (
    <group>
      <mesh position={[0, 0.25, 0]} rotation={[0, 0, 0]}>
        <boxGeometry args={[2.2, 0.4, 0.9]} />
        <Surface color={color} roughness={0.75} />
      </mesh>
      <mesh position={[0, 1.25, 0]}>
        <cylinderGeometry args={[0.05, 0.07, 2, 6]} />
        <Surface color={accent} roughness={0.8} />
      </mesh>
      <mesh position={[0.1, 1.55, 0]} rotation={[0, 0, -0.15]}>
        <coneGeometry args={[0.55, 1.3, 4]} />
        <Surface color="#e8e0cc" roughness={0.9} />
      </mesh>
    </group>
  );
}

function BridgeBody({ entity }: { entity: SceneEntity }) {
  const color = entityColor(entity);
  return (
    <group>
      {[0, 1, 2, 3].map((index) => (
        <mesh key={index} position={[-1.5 + index, 0.4, 0]}>
          <boxGeometry args={[1.1, 0.3, 1.4]} />
          <Surface color={color} roughness={0.9} />
        </mesh>
      ))}
      {[-1.5, 1.5].map((x) => (
        <mesh key={x} position={[x, 0.55, 0]}>
          <boxGeometry args={[0.18, 1.1, 1.5]} />
          <Surface color={color} roughness={0.9} />
        </mesh>
      ))}
    </group>
  );
}

function RoadBody({ entity }: { entity: SceneEntity }) {
  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.015, 0]}>
      <planeGeometry args={[2.4, 18]} />
      <meshStandardMaterial color={entityColor(entity)} roughness={0.95} />
    </mesh>
  );
}

function FlowerBody({ entity }: { entity: SceneEntity }) {
  const color = entityColor(entity);
  const stem = entityAccent(entity);
  return (
    <group>
      <mesh position={[0, 0.35, 0]}>
        <cylinderGeometry args={[0.03, 0.04, 0.7, 6]} />
        <Surface color={stem} roughness={0.9} />
      </mesh>
      {[0, 60, 120, 180, 240, 300].map((angle) => (
        <mesh
          key={angle}
          position={[Math.cos((angle * Math.PI) / 180) * 0.18, 0.75, Math.sin((angle * Math.PI) / 180) * 0.18]}
        >
          <sphereGeometry args={[0.12, 10, 8]} />
          <Surface color={color} roughness={0.6} />
        </mesh>
      ))}
      <mesh position={[0, 0.78, 0]}>
        <sphereGeometry args={[0.08, 10, 8]} />
        <meshStandardMaterial color="#ffd27a" emissive="#ffb84d" emissiveIntensity={0.8} />
      </mesh>
    </group>
  );
}

function DoorBody({ entity }: { entity: SceneEntity }) {
  const color = entityColor(entity);
  return (
    <group>
      <mesh position={[0, 1.05, 0]}>
        <boxGeometry args={[1.15, 2.1, 0.18]} />
        <Surface color={entityAccent(entity)} roughness={0.85} />
      </mesh>
      <mesh position={[0, 1.0, 0.11]}>
        <boxGeometry args={[0.92, 1.94, 0.1]} />
        <Surface color={color} roughness={0.7} emissive={entityEmissive(entity)} />
      </mesh>
    </group>
  );
}

function PortalBody({ entity, animate }: { entity: SceneEntity; animate: boolean }) {
  const color = entityColor(entity);
  const ref = useRef<THREE.Mesh>(null);
  useFrame(({ clock }) => {
    if (ref.current && animate) ref.current.rotation.z = clock.getElapsedTime() * 0.5;
  });
  return (
    <group position={[0, 1.1, 0]}>
      <mesh ref={ref}>
        <torusGeometry args={[0.9, 0.12, 12, 48]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={2.2} />
      </mesh>
      <mesh>
        <circleGeometry args={[0.82, 48]} />
        <meshBasicMaterial color={color} transparent opacity={0.25} side={THREE.DoubleSide} />
      </mesh>
    </group>
  );
}

function CrystalBody({ entity }: { entity: SceneEntity }) {
  const color = entityColor(entity);
  const emissive = Math.max(0.5, entityEmissive(entity));
  return (
    <group>
      <mesh position={[0, 0.8, 0]} rotation={[0.2, 0.4, 0]}>
        <octahedronGeometry args={[0.7, 0]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={emissive}
          roughness={0.1}
          metalness={0.2}
          transparent
          opacity={0.9}
        />
      </mesh>
      <mesh position={[0.6, 0.4, 0.2]} rotation={[0.4, 0.1, 0.3]}>
        <octahedronGeometry args={[0.34, 0]} />
        <Surface color={color} roughness={0.2} emissive={emissive} />
      </mesh>
    </group>
  );
}

function RockBody({ entity }: { entity: SceneEntity }) {
  return (
    <group>
      <mesh position={[0, 0.35, 0]} rotation={[0.2, 0.4, 0.1]}>
        <dodecahedronGeometry args={[0.6, 0]} />
        <Surface color={entityColor(entity)} roughness={1} />
      </mesh>
      <mesh position={[0.65, 0.18, 0.2]} rotation={[0.1, 0.8, 0]}>
        <dodecahedronGeometry args={[0.28, 0]} />
        <Surface color={entityColor(entity)} roughness={1} />
      </mesh>
    </group>
  );
}

function GrassBody({ entity }: { entity: SceneEntity }) {
  const count = Math.max(4, Math.round(attrNumber(entity, "count", 18)));
  const color = entityColor(entity);
  return (
    <group>
      {Array.from({ length: Math.min(count, 30) }, (_, index) => {
        const angle = index * 2.1;
        const radius = 0.2 + (index % 6) * 0.16;
        return (
          <mesh
            key={index}
            position={[Math.cos(angle) * radius, 0.2, Math.sin(angle) * radius]}
            rotation={[0, angle, 0.12]}
          >
            <coneGeometry args={[0.05, 0.45 + (index % 3) * 0.12, 4]} />
            <Surface color={color} roughness={0.9} />
          </mesh>
        );
      })}
    </group>
  );
}

function IslandBody({ entity }: { entity: SceneEntity }) {
  return (
    <group>
      <mesh position={[0, 0.1, 0]}>
        <cylinderGeometry args={[1.9, 2.3, 0.4, 12]} />
        <Surface color={entityColor(entity)} roughness={0.95} />
      </mesh>
      <mesh position={[0, 0.35, 0]}>
        <cylinderGeometry args={[1.35, 1.75, 0.25, 12]} />
        <Surface color={entityAccent(entity)} roughness={1} />
      </mesh>
    </group>
  );
}

function AbstractBody({ entity }: { entity: SceneEntity }) {
  const color = entityColor(entity);
  return (
    <group position={[0, 1, 0]}>
      <mesh>
        <icosahedronGeometry args={[0.8, 1]} />
        <Surface color={color} roughness={0.35} metalness={0.2} opacity={0.55} />
      </mesh>
      <mesh>
        <icosahedronGeometry args={[0.82, 1]} />
        <meshBasicMaterial color={color} wireframe transparent opacity={0.7} />
      </mesh>
    </group>
  );
}

function Body({ entity, style, animate }: { entity: SceneEntity; style: string; animate: boolean }) {
  switch (entity.kind) {
    case "castle":
      return <CastleBody entity={entity} style={style} />;
    case "moon":
    case "sun":
    case "planet": {
      const color = entityColor(entity);
      const emissive = Math.max(0.6, entityEmissive(entity));
      return (
        <mesh position={[0, 1.6, 0]}>
          <sphereGeometry args={[0.95, 32, 24]} />
          <meshStandardMaterial
            color={color}
            emissive={color}
            emissiveIntensity={emissive}
            roughness={0.55}
            metalness={0.05}
          />
        </mesh>
      );
    }
    case "water":
      return <WaterBody entity={entity} />;
    case "fog":
      return <FogBody entity={entity} />;
    case "tree":
      return <TreeBody entity={entity} />;
    case "forest":
      return <TreeBody entity={entity} forest />;
    case "mountain":
      return <MountainBody entity={entity} />;
    case "cloud":
      return <CloudBody entity={entity} />;
    case "star":
      return <StarBody entity={entity} />;
    case "fire":
      return <FireBody entity={entity} animate={animate} />;
    case "person":
      return <PersonBody entity={entity} />;
    case "creature":
      return <CreatureBody entity={entity} />;
    case "dragon":
      return <DragonBody entity={entity} />;
    case "bird": {
      const color = entityColor(entity);
      return (
        <group>
          <mesh rotation={[0, 0, 0.3]} position={[0, 1.4, 0]}>
            <coneGeometry args={[0.12, 0.8, 4]} />
            <Surface color={color} roughness={0.7} />
          </mesh>
          <mesh rotation={[0, 0, -0.3]} position={[0.4, 1.5, 0]}>
            <coneGeometry args={[0.08, 0.55, 4]} />
            <Surface color={color} roughness={0.7} />
          </mesh>
        </group>
      );
    }
    case "building":
      return <BuildingBody entity={entity} />;
    case "boat":
      return <BoatBody entity={entity} />;
    case "bridge":
      return <BridgeBody entity={entity} />;
    case "road":
      return <RoadBody entity={entity} />;
    case "flower":
      return <FlowerBody entity={entity} />;
    case "door":
      return <DoorBody entity={entity} />;
    case "portal":
      return <PortalBody entity={entity} animate={animate} />;
    case "crystal":
      return <CrystalBody entity={entity} />;
    case "rock":
      return <RockBody entity={entity} />;
    case "grass":
      return <GrassBody entity={entity} />;
    case "island":
      return <IslandBody entity={entity} />;
    default:
      return <AbstractBody entity={entity} />;
  }
}

export default function EntityMesh({
  entity,
  scene,
  selected,
  onSelect,
  animate = true,
}: {
  entity: SceneEntity;
  scene: SceneGraph;
  selected: boolean;
  onSelect: (entityId: string) => void;
  animate?: boolean;
}) {
  const floatRef = useRef<THREE.Group>(null);
  const size = entitySize(entity);
  const position = entity.transform.position;
  const rotation = entity.transform.rotation;
  const scale = entity.transform.scale.map((value) => value * size) as [number, number, number];
  const locked = isLocked(entity);
  const floating = Math.max(0, Math.min(1, scene.dynamics.floating));

  useFrame(({ clock }) => {
    if (!floatRef.current || !animate) return;
    const time = clock.getElapsedTime();
    floatRef.current.position.y = Math.sin(time * 0.9 + position[0]) * (0.03 + floating * 0.35);
    floatRef.current.rotation.z = floating * Math.sin(time * 0.6 + position[2]) * 0.03;
  });

  const handleClick = (event: ThreeEvent<MouseEvent>) => {
    event.stopPropagation();
    onSelect(entity.id);
  };

  return (
    <group
      position={position}
      rotation={rotation}
      scale={scale}
      visible={entity.visible}
      onClick={handleClick}
    >
      <group ref={floatRef}>
        <Body entity={entity} style={scene.style} animate={animate} />
      </group>
      {(selected || locked) && (
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.02, 0]}>
          <ringGeometry args={[1.15, 1.24, 48]} />
          <meshBasicMaterial
            color={selected ? "#79e8ff" : "#f5b642"}
            transparent
            opacity={selected ? 0.9 : 0.55}
            side={THREE.DoubleSide}
          />
        </mesh>
      )}
      {selected && (
        <Html position={[0, 2.9, 0]} center distanceFactor={12} zIndexRange={[20, 0]}>
          <div className="pointer-events-none whitespace-nowrap rounded-full border border-accent-glow/40 bg-background/85 px-2.5 py-1 text-[10px] font-medium text-accent-glow shadow-lg backdrop-blur">
            {entity.label}
            {locked ? " · locked" : ""}
          </div>
        </Html>
      )}
    </group>
  );
}
