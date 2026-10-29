import EvidenceMark from "@/components/evidence/EvidenceMark";

export default function Stat({
  label,
  value,
  detail,
  tone = "neutral",
  evidenceId,
}: {
  label: string;
  value: string;
  detail?: string;
  tone?: "neutral" | "signal" | "warning" | "danger";
  evidenceId?: string;
}) {
  const valueTone =
    tone === "signal"
      ? "text-signal"
      : tone === "warning"
        ? "text-lock"
        : tone === "danger"
          ? "text-danger"
          : "text-foreground";

  return (
    <div className="rounded-lg border border-surface-border bg-background/35 p-4">
      <div className="flex items-center justify-between gap-2">
        <div className="mono-label text-foreground/45">{label}</div>
        {evidenceId ? <EvidenceMark evidenceId={evidenceId} /> : null}
      </div>
      <div className={`mt-2 font-mono text-2xl font-semibold tabular-nums ${valueTone}`}>{value}</div>
      {detail ? <div className="mt-1 text-xs leading-5 text-foreground/45">{detail}</div> : null}
    </div>
  );
}
