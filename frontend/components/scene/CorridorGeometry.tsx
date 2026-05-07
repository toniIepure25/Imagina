"use client";

import { useRef, useMemo } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

interface Props {
  clarity: number;
  wallDistortion: number;
  textureDetail: number;
  colorSaturation: number;
}

export default function CorridorGeometry({ clarity, wallDistortion, textureDetail, colorSaturation }: Props) {
  const leftWallRef = useRef<THREE.Mesh>(null);
  const rightWallRef = useRef<THREE.Mesh>(null);

  const wallGeo = useMemo(() => new THREE.PlaneGeometry(20, 4, 64, 16), []);
  const depthMarks = useMemo(() => Array.from({ length: 12 }, (_, i) => -1.5 - i * 1.65), []);

  const baseHue = 0.61;
  const sat = 0.07 + colorSaturation * 0.48;
  const light = 0.06 + clarity * 0.19;
  const wallColor = new THREE.Color().setHSL(baseHue, sat, light);
  const floorColor = new THREE.Color().setHSL(baseHue - 0.07, sat * 0.75, light * 0.76);
  const ceilColor = new THREE.Color().setHSL(baseHue + 0.02, sat * 0.55, light * 0.58);
  const lineOpacity = 0.08 + textureDetail * 0.24 + clarity * 0.08;
  const ribOpacity = 0.15 + clarity * 0.35;

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    [leftWallRef, rightWallRef].forEach((ref) => {
      if (!ref.current) return;
      const geo = ref.current.geometry;
      const pos = geo.attributes.position;
      const base = (geo.userData.basePositions as Float32Array | undefined) ?? new Float32Array(pos.array as Float32Array);
      geo.userData.basePositions = base;
      for (let i = 0; i < pos.count; i++) {
        const y = base[i * 3 + 1];
        const z = base[i * 3 + 2];
        const distort = wallDistortion * 0.55 * Math.sin(y * 2 + z * 0.5 + t * 1.5);
        pos.setX(i, base[i * 3] + distort);
      }
      pos.needsUpdate = true;
    });
  });

  const roughness = 1 - textureDetail * 0.55;

  return (
    <group position={[0, 0, -5]}>
      {/* Floor */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0, 0]} receiveShadow>
        <planeGeometry args={[4, 20, 16, 64]} />
        <meshStandardMaterial color={floorColor} roughness={roughness} metalness={0.1} opacity={0.5 + clarity * 0.5} transparent />
      </mesh>

      {/* Ceiling */}
      <mesh rotation={[Math.PI / 2, 0, 0]} position={[0, 4, 0]}>
        <planeGeometry args={[4, 20, 16, 16]} />
        <meshStandardMaterial color={ceilColor} roughness={0.95} opacity={0.3 + clarity * 0.4} transparent />
      </mesh>

      {/* Structural ribs create corridor depth and a stronger vanishing point. */}
      {depthMarks.map((z, index) => (
        <group key={z} position={[0, 0, z]}>
          <mesh position={[-2.01, 2, 0]}>
            <boxGeometry args={[0.035, 3.75, 0.05]} />
            <meshBasicMaterial color="#78e8ff" transparent opacity={ribOpacity * (1 - index * 0.035)} />
          </mesh>
          <mesh position={[2.01, 2, 0]}>
            <boxGeometry args={[0.035, 3.75, 0.05]} />
            <meshBasicMaterial color="#78e8ff" transparent opacity={ribOpacity * (1 - index * 0.035)} />
          </mesh>
          <mesh position={[0, 3.92, 0]}>
            <boxGeometry args={[4.05, 0.035, 0.05]} />
            <meshBasicMaterial color="#8d8cff" transparent opacity={ribOpacity * 0.75 * (1 - index * 0.035)} />
          </mesh>
        </group>
      ))}

      {/* Ceiling and side light strips stay simple but read as premium research hardware. */}
      <mesh position={[0, 3.82, -5]}>
        <boxGeometry args={[0.08, 0.035, 17]} />
        <meshBasicMaterial color="#79e8ff" transparent opacity={0.14 + clarity * 0.34} />
      </mesh>
      <mesh position={[-1.88, 2.7, -5]}>
        <boxGeometry args={[0.035, 0.06, 15]} />
        <meshBasicMaterial color="#6b7cff" transparent opacity={0.10 + clarity * 0.28} />
      </mesh>
      <mesh position={[1.88, 2.7, -5]}>
        <boxGeometry args={[0.035, 0.06, 15]} />
        <meshBasicMaterial color="#6b7cff" transparent opacity={0.10 + clarity * 0.28} />
      </mesh>

      {/* Left wall */}
      <mesh ref={leftWallRef} rotation={[0, Math.PI / 2, 0]} position={[-2, 2, 0]}>
        <primitive object={wallGeo.clone()} attach="geometry" />
        <meshStandardMaterial color={wallColor} roughness={roughness} metalness={0.05} opacity={0.4 + clarity * 0.5} transparent />
      </mesh>

      {/* Right wall */}
      <mesh ref={rightWallRef} rotation={[0, -Math.PI / 2, 0]} position={[2, 2, 0]}>
        <primitive object={wallGeo.clone()} attach="geometry" />
        <meshStandardMaterial color={wallColor} roughness={roughness} metalness={0.05} opacity={0.4 + clarity * 0.5} transparent />
      </mesh>

      {/* Grid lines on floor when texture detail is high */}
      {textureDetail > 0.3 && (
        <gridHelper
          args={[20, 44, new THREE.Color(0.22, 0.34, 0.55), new THREE.Color(0.1, 0.18, 0.30)]}
          position={[0, 0.01, 0]}
        />
      )}

      {textureDetail > 0.15 && (
        <>
          <mesh rotation={[0, Math.PI / 2, 0]} position={[-1.985, 2, -5]}>
            <planeGeometry args={[16, 3.4, 16, 4]} />
            <meshBasicMaterial color="#79e8ff" transparent opacity={lineOpacity * 0.42} wireframe />
          </mesh>
          <mesh rotation={[0, -Math.PI / 2, 0]} position={[1.985, 2, -5]}>
            <planeGeometry args={[16, 3.4, 16, 4]} />
            <meshBasicMaterial color="#79e8ff" transparent opacity={lineOpacity * 0.42} wireframe />
          </mesh>
        </>
      )}
    </group>
  );
}
