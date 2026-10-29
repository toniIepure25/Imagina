"use client";

import { Line } from "@react-three/drei";
import type { TraceSet } from "@/lib/sceneCompare";
import { entitySize } from "../sceneUtils";

export default function SceneTrace({ traces }: { traces: TraceSet }) {
  if (!traces.shown) return null;
  return (
    <group name="scene-trace">
      {traces.items.map(({ entity, state, nextPosition }) => {
        const size = Math.max(0.3, entitySize(entity) * 0.9);
        const color = state === "removed" ? "#7f8ba3" : "#e8b45a";
        return (
          <group key={`${state}-${entity.id}`}>
            <mesh
              position={entity.transform.position}
              rotation={entity.transform.rotation}
              renderOrder={-1}
            >
              <boxGeometry args={[size, size, size]} />
              <meshBasicMaterial
                color={color}
                wireframe
                transparent
                opacity={state === "removed" ? 0.16 : 0.22}
                depthWrite={false}
              />
            </mesh>
            {nextPosition ? (
              <Line
                points={[entity.transform.position, nextPosition]}
                color={color}
                lineWidth={1}
                dashed
                dashSize={0.22}
                gapSize={0.16}
                transparent
                opacity={0.45}
              />
            ) : null}
          </group>
        );
      })}
    </group>
  );
}
