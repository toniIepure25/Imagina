import { CLAIM_CEILING } from "@/lib/claims";

export default function ClaimBadge({ className = "" }: { className?: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border border-signal/25 bg-signal/[0.06] px-2.5 py-1 font-mono text-[11px] uppercase tracking-[0.14em] text-signal/80 ${className}`}
      title="Behavioural proxy methods only; no neural decoding"
    >
      <span className="h-1 w-1 rounded-full bg-signal/80" aria-hidden="true" />
      {CLAIM_CEILING.replaceAll("_", " ")}
    </span>
  );
}
