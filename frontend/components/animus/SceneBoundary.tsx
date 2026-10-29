"use client";

import { Component, type ErrorInfo, type ReactNode } from "react";
import type { SceneGraph } from "@/lib/animusStudioApi";
import SceneSketch from "./SceneSketch";

export default class SceneBoundary extends Component<
  { scene: SceneGraph; children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    if (process.env.NODE_ENV !== "production") {
      console.error("ANIMUS scene render failed", error, info.componentStack);
    }
  }

  render() {
    if (this.state.failed) {
      return (
        <div className="relative h-full min-h-[320px] overflow-hidden">
          <SceneSketch scene={this.props.scene} className="opacity-80" showLabels />
          <div className="absolute inset-x-4 bottom-4 rounded-lg border border-lock/30 bg-[#0b0d10]/90 p-3 text-[11px] leading-relaxed text-foreground/65 backdrop-blur">
            The 3D stage could not start in this browser. The scene graph is still available in Structure, and the
            sketch above is a static top-down projection.
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
