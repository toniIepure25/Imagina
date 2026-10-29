"use client";

import { useId, type ReactNode } from "react";
import EvidenceMark from "@/components/evidence/EvidenceMark";

export type ChartTable = {
  columns: string[];
  rows: Array<Array<string | number>>;
};

export default function ChartFrame({
  title,
  description,
  evidenceId,
  table,
  children,
  className = "",
}: {
  title: string;
  description?: string;
  evidenceId?: string;
  table: ChartTable;
  children: ReactNode;
  className?: string;
}) {
  const descriptionId = useId();
  const hasRows = table.rows.length > 0;

  return (
    <figure className={`rounded-xl border border-surface-border bg-white/[0.02] p-4 ${className}`}>
      <figcaption>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-medium text-foreground/75">{title}</h3>
            {evidenceId ? <EvidenceMark evidenceId={evidenceId} /> : null}
          </div>
          <span className="font-mono text-[11px] text-foreground/30">chart + table</span>
        </div>
        {description ? (
          <p id={descriptionId} className="mt-1 text-[11px] leading-5 text-foreground/40">
            {description}
          </p>
        ) : null}
      </figcaption>

      <div className="mt-3" aria-hidden="true">
        {hasRows ? children : <p className="py-8 text-center text-xs text-foreground/35">Waiting for data…</p>}
      </div>

      <details className="mt-3 border-t border-surface-border pt-3">
        <summary className="cursor-pointer text-[11px] text-foreground/45 hover:text-foreground/70">
          View as table
        </summary>
        <div className="mt-2 max-h-64 overflow-auto">
          <table className="w-full min-w-[480px] border-collapse text-left text-[11px]">
            <caption className="sr-only">{title} data table</caption>
            <thead>
              <tr className="border-b border-surface-border text-foreground/40">
                {table.columns.map((column) => (
                  <th key={column} scope="col" className="px-2 py-1.5 font-medium">
                    {column}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="tabular-nums text-foreground/60">
              {table.rows.map((row, rowIndex) => (
                <tr key={rowIndex} className="border-b border-surface-border/50 last:border-0">
                  {row.map((cell, cellIndex) => (
                    <td key={`${rowIndex}-${cellIndex}`} className="px-2 py-1.5">
                      {cell}
                    </td>
                  ))}
                </tr>
              ))}
              {!hasRows ? (
                <tr>
                  <td colSpan={table.columns.length} className="px-2 py-4 text-center text-foreground/35">
                    No rows yet.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </details>
    </figure>
  );
}
