"use client";

import { useRef, useMemo } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

interface Props {
  stability: number;
}

const COUNT = 200;

function seededUnit(index: number, salt: number) {
  const x = Math.sin(index * 12.9898 + salt * 78.233) * 43758.5453;
  return x - Math.floor(x);
}

export default function ParticleField({ stability }: Props) {
  const ref = useRef<THREE.Points>(null);

  const positions = useMemo(() => {
    const arr = new Float32Array(COUNT * 3);
    for (let i = 0; i < COUNT; i++) {
      arr[i * 3] = (seededUnit(i, 1) - 0.5) * 4;
      arr[i * 3 + 1] = seededUnit(i, 2) * 4;
      arr[i * 3 + 2] = -seededUnit(i, 3) * 20;
    }
    return arr;
  }, []);

  useFrame(({ clock }) => {
    if (!ref.current) return;
    const t = clock.getElapsedTime();
    const pos = ref.current.geometry.attributes.position;
    const chaosScale = (1 - stability) * 0.28;
    const driftSpeed = 0.002 + stability * 0.005;

    for (let i = 0; i < COUNT; i++) {
      let y = pos.getY(i) + driftSpeed;
      if (y > 4) y = 0;
      const baseX = positions[i * 3];
      const baseZ = positions[i * 3 + 2];
      const xJitter = chaosScale * Math.sin(t * 3 + i);
      const zJitter = chaosScale * Math.cos(t * 2.5 + i * 0.7);
      pos.setY(i, y);
      pos.setX(i, baseX + xJitter);
      pos.setZ(i, baseZ + zJitter);
    }
    pos.needsUpdate = true;
  });

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} count={COUNT} />
      </bufferGeometry>
      <pointsMaterial size={0.03} color="#aaaaff" transparent opacity={0.4 + stability * 0.4} sizeAttenuation />
    </points>
  );
}
