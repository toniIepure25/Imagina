"use client";

import { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

interface Props {
  strength: number;
}

export default function BreathingCue({ strength }: Props) {
  const ref = useRef<THREE.Mesh>(null);

  useFrame(({ clock }) => {
    if (!ref.current || strength < 0.1) return;
    const t = clock.getElapsedTime();
    const breathCycle = Math.sin(t * 0.8) * 0.5 + 0.5;
    const scale = 0.36 + breathCycle * strength * 0.52;
    ref.current.scale.setScalar(scale);
    ref.current.lookAt(0, 1.6, 5);
    (ref.current.material as THREE.MeshBasicMaterial).opacity = strength * (0.10 + 0.22 * breathCycle);
  });

  if (strength < 0.1) return null;

  return (
    <mesh ref={ref} position={[0, 1.6, 1.8]}>
      <ringGeometry args={[0.72, 0.78, 72]} />
      <meshBasicMaterial color="#79e8ff" transparent opacity={0.15} side={THREE.DoubleSide} depthWrite={false} />
    </mesh>
  );
}
