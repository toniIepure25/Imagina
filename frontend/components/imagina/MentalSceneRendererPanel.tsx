"use client";

interface SceneParams {
  clarity: number; fog: number; brightness: number; color_saturation: number;
  motion_speed: number; stability_anchor: number; detail_density: number;
  object_scale: number; object_sharpness: number; background_complexity: number;
  particle_density: number; visual_noise: number; breathing_rate: number; calmness: number;
}

interface SceneState {
  template_id: string; phase: string; scene_parameters: SceneParams;
  derived_from: { iqi_proxy: number; pid_proxy: number; safety_state: string; feedback_type: string };
  render_instruction: string; visualization_boundary?: string;
}

interface Template { title: string; category: string; base_scene: { background_type: string; base_colors: string[]; }; }

interface MSRProps { sceneState: SceneState | null; template: Template | null; onRefresh: () => void; }

const BG_MAP: Record<string, string> = {
  dark: "radial-gradient(circle at center, rgba(30,10,40,1) 0%, rgba(5,0,15,1) 100%)",
  grid: "linear-gradient(180deg, rgba(10,10,40,1) 0%, rgba(0,0,20,1) 100%)",
  nature: "linear-gradient(180deg, rgba(20,50,20,1) 0%, rgba(5,20,5,1) 100%)",
  beach: "linear-gradient(180deg, rgba(40,60,80,1) 0%, rgba(80,60,40,1) 100%)",
  room: "linear-gradient(180deg, rgba(30,30,40,1) 0%, rgba(15,15,25,1) 100%)",
  symbolic: "radial-gradient(circle at 50% 60%, rgba(40,20,60,1) 0%, rgba(5,0,20,1) 100%)",
};

export function MentalSceneRendererPanel({ sceneState, template, onRefresh }: MSRProps) {
  if (!sceneState) {
    return (
      <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-pink-500/50">
        <div className="text-foreground/40 uppercase tracking-[0.1em]">Scene Renderer (V22)</div>
        <div className="text-foreground/50">Run a guided session to see the symbolic scene.</div>
        <button onClick={onRefresh} className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">Refresh</button>
      </div>
    );
  }

  const p = sceneState.scene_parameters;
  const px = sceneState.derived_from;
  const bg = BG_MAP[template?.base_scene?.background_type || "dark"] || BG_MAP["dark"];
  const colors = template?.base_scene?.base_colors || ["#884488", "#220022", "#442244"];

  const csx = {
    "--clarity": p.clarity, "--fog": p.fog, "--brightness": p.brightness,
    "--saturation": p.color_saturation, "--motion": p.motion_speed,
    "--detail": p.detail_density, "--stability": p.stability_anchor,
    "--scale": p.object_scale, "--sharpness": p.object_sharpness,
    "--calmness": p.calmness, "--noise": p.visual_noise,
    "--bg-gradient": bg, "--color1": colors[0], "--color2": colors[1], "--color3": colors[2],
    "--breathing-rate": `${4 - p.breathing_rate * 3}s`,
  } as React.CSSProperties;

  return (
    <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-pink-500/50">
      <div className="flex justify-between">
        <div className="text-foreground/40 uppercase tracking-[0.1em]">Scene Renderer (V22)</div>
        <span className="text-pink-300 text-[8px]">{template?.title || sceneState.template_id}</span>
      </div>
      <div style={{ ...csx, width: "100%", height: 120, borderRadius: 8, overflow: "hidden", position: "relative" }}>
        <div style={{ width: "100%", height: "100%", background: "var(--bg-gradient)", filter: `brightness(${0.5 + p.brightness * 0.8}) blur(${p.fog * 8}px)`, transition: "filter 0.5s" }} />
        <div style={{ position: "absolute", top: "50%", left: "50%", transform: "translate(-50%, -50%)", width: `${40 + p.object_scale * 40}px`, height: `${40 + p.object_scale * 40}px`, borderRadius: "50%", background: `radial-gradient(circle, ${colors[0]}55, ${colors[2]}88)`, filter: `blur(${(1 - p.object_sharpness) * 6}px) saturate(${0.3 + p.color_saturation * 1.5})`, opacity: p.clarity, boxShadow: `0 0 ${p.clarity * 30}px ${colors[0]}66` }} />
        {p.particle_density > 0.1 && (
          <div style={{ position: "absolute", inset: 0, opacity: p.particle_density, background: `radial-gradient(circle at ${30 + p.motion_speed * 40}% ${70 - p.motion_speed * 30}%, ${colors[1]}44 0%, transparent 60%)`, transition: "all 0.8s" }} />
        )}
        <div style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0, background: `linear-gradient(180deg, rgba(0,0,0,${p.fog.toFixed(2)}) 0%, transparent 50%)` }} />
      </div>

      <div className="grid grid-cols-3 gap-1 text-center text-[8px]">
        <div className="p-1 rounded bg-surface/30"><span className="text-foreground/30">IQI</span><br /><span className="text-foreground/60">{px.iqi_proxy?.toFixed(2)}</span></div>
        <div className="p-1 rounded bg-surface/30"><span className="text-foreground/30">PID</span><br /><span className="text-foreground/60">{px.pid_proxy?.toFixed(2)}</span></div>
        <div className="p-1 rounded bg-surface/30"><span className="text-foreground/30">Phase</span><br /><span className="text-foreground/60">{sceneState.phase}</span></div>
      </div>

      <div className="text-foreground/20 text-[7px]">{sceneState.visualization_boundary}</div>
    </div>
  );
}
