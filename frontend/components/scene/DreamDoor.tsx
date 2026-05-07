"use client";

import * as THREE from "three";

interface Props {
  complexity: number;
}

export default function DreamDoor({ complexity }: Props) {
  const doorCount = Math.max(1, Math.round(complexity * 5));
  const doors = [];
  for (let i = 0; i < doorCount; i++) {
    const z = -4 - i * 4;
    const side = i % 2 === 0 ? -1.95 : 1.95;
    const rotY = side < 0 ? Math.PI / 2 : -Math.PI / 2;
    const hue = 0.58 + complexity * 0.08;
    const color = new THREE.Color().setHSL(hue, 0.38, 0.12 + complexity * 0.12);
    const glow = 0.2 + complexity * 0.55;

    doors.push(
      <group key={i} position={[side, 1.2, z]}>
        <mesh rotation={[0, rotY, 0]}>
          <planeGeometry args={[1.2, 2.4]} />
          <meshStandardMaterial color={color} roughness={0.52} metalness={0.28} opacity={0.45 + complexity * 0.45} transparent />
        </mesh>
        <mesh rotation={[0, rotY, 0]} position={[0, 0, 0.015]}>
          <ringGeometry args={[0.47, 0.49, 4]} />
          <meshBasicMaterial color="#79e8ff" transparent opacity={glow * 0.55} side={THREE.DoubleSide} />
        </mesh>
        <mesh rotation={[0, rotY, Math.PI / 2]} position={[0, 0.52, 0.025]}>
          <boxGeometry args={[0.025, 0.58, 0.025]} />
          <meshBasicMaterial color="#79e8ff" transparent opacity={glow * 0.45} />
        </mesh>
        <mesh rotation={[0, rotY, Math.PI / 2]} position={[0, -0.52, 0.025]}>
          <boxGeometry args={[0.025, 0.58, 0.025]} />
          <meshBasicMaterial color="#79e8ff" transparent opacity={glow * 0.28} />
        </mesh>
        {complexity > 0.5 && (
          <mesh rotation={[0, rotY, 0]} position={[0.36, 0, 0.04]}>
            <sphereGeometry args={[0.06, 8, 8]} />
            <meshStandardMaterial color="#d7fbff" emissive="#79e8ff" emissiveIntensity={0.25} metalness={0.8} roughness={0.2} />
          </mesh>
        )}
      </group>
    );
  }
  return <>{doors}</>;
}
