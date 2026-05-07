"use client";

interface SliderProps {
  label: string;
  value: number;
  min?: number;
  max?: number;
  onChange: (v: number) => void;
}

export default function Slider({ label, value, min = 1, max = 10, onChange }: SliderProps) {
  return (
    <div className="flex items-center gap-3">
      <label className="text-xs text-foreground/60 w-24 shrink-0">{label}</label>
      <input
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="flex-1 accent-accent h-1.5 rounded-full"
      />
      <span className="text-xs text-foreground/80 w-6 text-right font-mono">{value}</span>
    </div>
  );
}
