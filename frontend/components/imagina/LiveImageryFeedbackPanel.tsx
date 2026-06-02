"use client";

interface SceneFeedback { clarity: number; fog: number; brightness: number; color_saturation: number; motion_speed: number; stability_anchor: number; detail_density: number; audio_calmness: number; }

interface Feedback { feedback_type: string; guidance_text: string; scene_feedback: SceneFeedback; why: string[]; safety_state: string; }

interface LFPProps { feedback: Feedback | null; onRefresh: () => void; }

export function LiveImageryFeedbackPanel({ feedback, onRefresh }: LFPProps) {
  if (!feedback) return null;

  const sf = feedback.scene_feedback || {} as SceneFeedback;
  const bars: [string, number][] = [
    ["Clarity", sf.clarity || 0], ["Fog", sf.fog || 0], ["Brightness", sf.brightness || 0],
    ["Saturation", sf.color_saturation || 0], ["Motion", sf.motion_speed || 0],
    ["Anchor", sf.stability_anchor || 0], ["Detail", sf.detail_density || 0],
    ["Calmness", sf.audio_calmness || 0],
  ];

  return (
    <div className="glass panel-glow p-4 space-y-3 text-[10px] border-l-2 border-pink-500/50">
      <div className="text-foreground/40 uppercase tracking-[0.1em]">Live Feedback (V20)</div>
      <div className="text-pink-300 text-[9px]">{feedback.guidance_text?.slice(0, 120)}</div>
      <div className="text-foreground/30 text-[8px]">Type: {feedback.feedback_type} · Safety: {feedback.safety_state}</div>
      <div className="space-y-1">
        {bars.map(([label, val]) => (
          <div key={label} className="flex gap-2 text-[8px] items-center">
            <span className="text-foreground/40 w-16">{label}</span>
            <div className="flex-1 bg-surface-border rounded h-1"><div className="bg-pink-400 h-1 rounded" style={{ width: `${(val || 0) * 100}%` }} /></div>
          </div>
        ))}
      </div>
      <button onClick={onRefresh} className="px-3 py-1.5 rounded bg-surface border border-surface-border text-foreground/50 hover:bg-surface/50">Refresh</button>
      <div className="text-foreground/20 text-[7px]">Self-report proxy — not neural measurement, not BCI, not mind-reading.</div>
    </div>
  );
}
