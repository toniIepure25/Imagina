"use client";

import { useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { PerspectiveCamera } from "@react-three/drei";
import * as THREE from "three";
import { SceneParams, DEFAULT_SCENE_PARAMS } from "@/lib/feedbackMapping";
import CorridorGeometry from "./CorridorGeometry";
import FeedbackLighting from "./FeedbackLighting";
import ParticleField from "./ParticleField";
import DreamDoor from "./DreamDoor";
import BreathingCue from "./BreathingCue";

interface Props {
  params?: SceneParams;
}

function CameraRig({ params }: { params: SceneParams }) {
  const cameraRef = useRef<THREE.PerspectiveCamera>(null);
  const target = useRef(new THREE.Vector3(0, 1.55, -7));

  useFrame(({ clock }) => {
    const camera = cameraRef.current;
    if (!camera) return;
    const t = clock.getElapsedTime();
    const instability = Math.max(params.wallDistortion, 1 - params.particleStability);
    const fatigueCalm = Math.max(0, params.breathingCueStrength - 0.45);
    const drift = Math.max(0.015, 0.075 * instability * (1 - fatigueCalm * 0.6));
    const breath = 0.025 + params.breathingCueStrength * 0.025;

    camera.position.x = Math.sin(t * 0.34) * drift;
    camera.position.y = 1.55 + Math.sin(t * 0.62) * breath;
    camera.position.z = 5 + Math.cos(t * 0.28) * drift * 2;
    target.current.set(Math.sin(t * 0.24) * drift * 1.4, 1.55, -7.5 - params.clarity * 1.5);
    camera.lookAt(target.current);
  });

  return <PerspectiveCamera ref={cameraRef} makeDefault position={[0, 1.6, 5]} fov={60} />;
}

function AtmosphericVeils({ fogDensity, clarity }: { fogDensity: number; clarity: number }) {
  const opacity = 0.035 + fogDensity * 0.085;
  return (
    <group>
      {[-5, -9, -13, -17].map((z, index) => (
        <mesh key={z} position={[0, 2, z]} rotation={[0, 0, 0]}>
          <planeGeometry args={[6.5 + index * 0.9, 4.6]} />
          <meshBasicMaterial
            color={index % 2 === 0 ? "#17204d" : "#103845"}
            transparent
            opacity={opacity * (1.05 - clarity * 0.55)}
            depthWrite={false}
            side={THREE.DoubleSide}
          />
        </mesh>
      ))}
    </group>
  );
}

export default function DreamCorridorScene({ params = DEFAULT_SCENE_PARAMS }: Props) {
  const fogNear = 2 + (1 - params.fogDensity) * 13;
  const fogFar = 9 + (1 - params.fogDensity) * 36;

  return (
    <div className="cinematic-frame w-full h-full relative overflow-hidden bg-[#050711]">
      <div className="absolute left-4 bottom-4 z-20 max-w-xs rounded-lg border border-white/10 bg-background/65 p-3 text-[11px] text-foreground/72 backdrop-blur-md panel-glow">
        <div className="mb-1 text-[10px] uppercase tracking-[0.18em] text-accent-glow/80">Scene Mapping</div>
        <div>Clarity = IQI proxy</div>
        <div>Fog = uncertainty/fatigue</div>
        <div>Wall distortion = instability</div>
        <div>Doors = curriculum progression</div>
        <div>Pulse = reset cue</div>
      </div>
      {params.blur > 0.3 && (
        <div
          className="absolute inset-0 z-10 pointer-events-none transition-[backdrop-filter] duration-500"
          style={{ backdropFilter: `blur(${Math.max(0, params.blur - 0.25) * 5}px)` }}
        />
      )}
      <Canvas className="w-full h-full" gl={{ antialias: true, powerPreference: "high-performance" }} dpr={[1, 1.75]}>
        <CameraRig params={params} />
        <fog attach="fog" args={["#070814", fogNear, fogFar]} />
        <color attach="background" args={["#050711"]} />
        <ambientLight intensity={0.06 + params.clarity * 0.06} />
        <CorridorGeometry
          clarity={params.clarity}
          wallDistortion={params.wallDistortion}
          textureDetail={params.textureDetail}
          colorSaturation={params.colorSaturation}
        />
        <FeedbackLighting stability={params.lightStability} clarity={params.clarity} />
        <AtmosphericVeils fogDensity={params.fogDensity} clarity={params.clarity} />
        <ParticleField stability={params.particleStability} />
        {params.doorComplexity > 0 && <DreamDoor complexity={params.doorComplexity} />}
        <BreathingCue strength={params.breathingCueStrength} />
      </Canvas>
    </div>
  );
}
