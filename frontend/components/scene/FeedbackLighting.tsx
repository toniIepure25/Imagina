"use client";

import { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

interface Props {
  stability: number;
  clarity?: number;
}

export default function FeedbackLighting({ stability, clarity = 0.5 }: Props) {
  const light1 = useRef<THREE.PointLight>(null);
  const light2 = useRef<THREE.PointLight>(null);
  const light3 = useRef<THREE.PointLight>(null);

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    const flickerAmount = (1 - stability) * 0.48;

    [light1, light2, light3].forEach((ref, i) => {
      if (!ref.current) return;
      const base = 0.28 + stability * 0.42 + clarity * 0.22;
      const flicker = flickerAmount * Math.sin(t * (4.5 + i * 1.2) + i * 2) * 0.5;
      ref.current.intensity = Math.max(0.05, base + flicker);
    });
  });

  return (
    <>
      <pointLight ref={light1} position={[0, 3.4, -2]} color="#77ddff" distance={12} decay={2} />
      <pointLight ref={light2} position={[0, 3.4, -8]} color="#8c8cff" distance={14} decay={2} />
      <pointLight ref={light3} position={[0, 3.4, -14]} color="#55c8ff" distance={16} decay={2} />
    </>
  );
}
