"use client";

const LEVELS = [
  "Breath", "Corridor", "Walls", "Lighting", "Texture", "Doors", "Room", "Return"
];

export default function CurriculumTimeline({ currentLevel }: { currentLevel: number }) {
  return (
    <div className="flex items-center gap-1 px-4 py-2 overflow-x-auto border-b border-surface-border/70 bg-background/40">
      {LEVELS.map((name, i) => {
        const lvl = i + 1;
        const active = lvl === currentLevel;
        const done = lvl < currentLevel;
        return (
          <div key={lvl} className="flex items-center gap-1">
            <div
              className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-all duration-300 ${
                active ? "bg-accent text-white shadow-[0_0_20px_rgba(121,232,255,0.35)]" : done ? "bg-accent/25 text-accent-glow" : "bg-surface text-foreground/30"
              }`}
            >
              {lvl}
            </div>
            <span className={`text-[10px] whitespace-nowrap ${active ? "text-foreground/80" : "text-foreground/30"}`}>
              {name}
            </span>
            {i < LEVELS.length - 1 && <div className={`w-3 h-px ${done ? "bg-accent/40" : "bg-surface-border"}`} />}
          </div>
        );
      })}
    </div>
  );
}
