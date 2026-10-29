"use client";

import type { ProfileDimension } from "@/lib/animusStudioApi";

const STATUS_LABEL: Record<string, string> = {
  no_evidence: "no evidence",
  collecting: "collecting",
  provisional: "provisional",
  moderate_evidence: "moderate",
};

function statusTone(status: string): string {
  if (status === "moderate_evidence") return "border-[#2d6b58]/40 text-[#245c4c]";
  if (status === "provisional") return "border-[#8b6a2f]/40 text-[#74551f]";
  if (status === "collecting") return "border-[#1b1d1f]/25 text-[#5d5b54]";
  return "border-[#1b1d1f]/15 text-[#8a857a]";
}

function fmt(value: number | null, digits = 2): string {
  return value === null ? "—" : value.toFixed(digits);
}

export function IntervalPlot({ dimension }: { dimension: ProfileDimension }) {
  const isBrier = dimension.id === "calibration" && typeof dimension.brier_score === "number";
  const value = isBrier ? dimension.brier_score ?? null : dimension.estimate;
  const uncertainty = Math.max(0, Math.min(1, dimension.uncertainty));
  if (value === null) {
    return (
      <svg viewBox="0 0 120 18" className="h-[18px] w-[120px]" role="img" aria-label="No estimate yet">
        <line x1="4" y1="9" x2="116" y2="9" stroke="#b8b0a0" strokeDasharray="2 3" />
        <text x="60" y="13" textAnchor="middle" fontSize="11" fill="#8a857a" fontFamily="ui-monospace, monospace">
          no estimate
        </text>
      </svg>
    );
  }
  const x = 4 + value * 112;
  const left = 4 + Math.max(0, value - uncertainty) * 112;
  const right = 4 + Math.min(1, value + uncertainty) * 112;
  return (
    <svg
      viewBox="0 0 120 18"
      className="h-[18px] w-[120px]"
      role="img"
      aria-label={`Estimate ${value.toFixed(2)}, uncertainty band ${Math.max(0, value - uncertainty).toFixed(2)} to ${Math.min(1, value + uncertainty).toFixed(2)}${isBrier ? ", lower is better" : ""}`}
    >
      <line x1="4" y1="9" x2="116" y2="9" stroke="#d6cfc1" />
      <line x1="4" y1="5" x2="4" y2="13" stroke="#b8b0a0" />
      <line x1="116" y1="5" x2="116" y2="13" stroke="#b8b0a0" />
      {isBrier ? (
        <text x="4" y="17" fontSize="11" fill="#8a857a" fontFamily="ui-monospace, monospace">better</text>
      ) : null}
      <line x1={left} y1="9" x2={right} y2="9" stroke="#2d6b58" strokeWidth="3" opacity="0.35" strokeLinecap="round" />
      <circle cx={x} cy="9" r="3.4" fill="#1b1d1f" stroke="#f3eee2" strokeWidth="1.2" />
    </svg>
  );
}

function nextEvidence(dimensions: ProfileDimension[]): { label: string; reason: string } {
  const eligible = dimensions.filter((dimension) => dimension.id !== "calibration");
  if (!eligible.length) return { label: "Practice recall", reason: "No dimension has evidence yet." };
  const sorted = eligible.slice().sort((a, b) => a.n - b.n);
  const target = sorted[0];
  return {
    label: target.label,
    reason:
      target.n === 0
        ? "No trials yet; one short recall run would create the first evidence."
        : `${target.n} trial${target.n === 1 ? "" : "s"} so far; another run would narrow the interval.`,
  };
}

export default function EvidenceLedger({
  dimensions,
  trialCount,
  loading,
}: {
  dimensions: ProfileDimension[];
  trialCount: number;
  loading: boolean;
}) {
  const suggestion = nextEvidence(dimensions);
  return (
    <section aria-labelledby="evidence-ledger-title">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <p className="dossier-label">Evidence ledger</p>
          <h2 id="evidence-ledger-title" className="dossier-display mt-1 text-2xl text-ink">
            Separate estimates, never a composite
          </h2>
        </div>
        <span className="font-mono text-[11px] uppercase tracking-[0.16em] text-ink-muted">
          {trialCount} local trial{trialCount === 1 ? "" : "s"}
        </span>
      </div>

      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-[700px] border-collapse text-left">
          <caption className="sr-only">
            Behavioural dimensions with estimate, uncertainty, trial count, reliability, and status
          </caption>
          <thead>
            <tr className="border-b border-rule/70">
              {["Construct", "Estimate", "n", "Reliability", "Status", "Read as"].map((heading) => (
                <th key={heading} scope="col" className="py-2 pr-4 font-mono text-[11px] font-normal uppercase tracking-[0.18em] text-ink-muted">
                  {heading}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={6} className="py-6 text-[11px] text-ink-muted">Loading local profile…</td>
              </tr>
            ) : dimensions.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-6 text-[11px] text-ink-muted">No dimensions returned by the local profile.</td>
              </tr>
            ) : (
              dimensions.map((dimension) => {
                const isBrier = dimension.id === "calibration" && typeof dimension.brier_score === "number";
                return (
                  <tr key={dimension.id} className="border-b border-rule/45 align-top">
                    <th scope="row" className="max-w-[230px] py-3 pr-4 text-left">
                      <span className="block text-[12px] font-medium text-ink">{dimension.label}</span>
                      <span className="mt-0.5 block text-[11px] leading-relaxed text-ink-muted">{dimension.construct}</span>
                    </th>
                    <td className="py-3 pr-4">
                      <span className="block font-mono text-sm tabular-nums text-ink">
                        {isBrier ? fmt(dimension.brier_score ?? null, 3) : fmt(dimension.estimate, 2)}
                        {isBrier ? <span className="ml-1 text-[11px] text-ink-muted">Brier</span> : null}
                      </span>
                      <span className="mt-1 block text-[11px] text-ink-muted">
                        {isBrier ? "lower is better" : dimension.estimate === null ? "not enough evidence" : "± uncertainty band"}
                      </span>
                    </td>
                    <td className="py-3 pr-4 font-mono text-[11px] tabular-nums text-ink">{dimension.n}</td>
                    <td className="py-3 pr-4">
                      <IntervalPlot dimension={dimension} />
                      <span className="mt-1 block font-mono text-[11px] text-ink-muted">
                        r = {dimension.reliability.toFixed(2)}
                      </span>
                    </td>
                    <td className="py-3 pr-4">
                      <span className={`inline-flex rounded-full border px-2 py-0.5 font-mono text-[11px] uppercase tracking-[0.12em] ${statusTone(dimension.status)}`}>
                        {STATUS_LABEL[dimension.status] ?? dimension.status}
                      </span>
                    </td>
                    <td className="max-w-[240px] py-3 pr-2 text-[11px] leading-relaxed text-ink-muted">
                      {dimension.n < 3
                        ? "At least three trials are required before the estimate is interpreted."
                        : dimension.description}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      <div className="mt-5 flex flex-wrap items-start justify-between gap-3 border border-rule/70 bg-[#f5f0e4]/70 p-3">
        <div>
          <p className="dossier-label">Next useful evidence</p>
          <p className="mt-1 text-[12px] font-medium text-ink">{suggestion.label}</p>
          <p className="mt-0.5 text-[11px] leading-relaxed text-ink-muted">{suggestion.reason}</p>
        </div>
        <p className="max-w-[330px] text-[11px] leading-relaxed text-ink-muted">
          A suggestion, not a prescription. The adaptive selector remains the source of task difficulty.
          Calibration is shown separately and is never folded into a total.
        </p>
      </div>
    </section>
  );
}
