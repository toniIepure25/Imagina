export default function Meter({
  label,
  value,
  detail,
  tone = "mint",
  className = "",
}: {
  label: string;
  value: number;
  detail?: string;
  tone?: "mint" | "ember" | "iris";
  className?: string;
}) {
  const clamped = Math.max(0, Math.min(1, value));
  const bar =
    tone === "ember" ? "bg-lumen-ember/80" : tone === "iris" ? "bg-lumen-iris/80" : "bg-lumen-mint/80";

  return (
    <div className={className}>
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-[11px] text-foreground/55">{label}</span>
        <span className="font-mono text-[11px] tabular-nums text-foreground/35">
          {Math.round(clamped * 100)}
        </span>
      </div>
      <div
        role="progressbar"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(clamped * 100)}
        className="mt-1.5 h-px overflow-hidden bg-white/10"
      >
        <span className={`block h-full ${bar}`} style={{ width: `${clamped * 100}%` }} />
      </div>
      {detail ? <p className="mt-1.5 text-[11px] leading-4 text-foreground/30">{detail}</p> : null}
    </div>
  );
}
