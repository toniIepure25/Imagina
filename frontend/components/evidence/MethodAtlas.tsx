"use client";

import Link from "next/link";
import { useDeferredValue, useMemo, useState } from "react";
import BoundaryNote from "@/components/platform/BoundaryNote";
import PageHeader from "@/components/platform/PageHeader";
import Panel from "@/components/platform/Panel";
import ClaimBadge from "@/components/platform/ClaimBadge";
import GlassBoxToggle from "@/components/evidence/GlassBoxToggle";
import auditRaw from "@/lib/evidence/audit.json";
import { EVIDENCE_ENTRIES, EVIDENCE_REGISTRY } from "@/lib/evidence/registry";
import {
  EVIDENCE_KIND_COPY,
  EVIDENCE_KIND_LABEL,
  EVIDENCE_KIND_LETTER,
  type EvidenceAudit,
  type EvidenceKind,
  type EvidenceScope,
} from "@/lib/evidence/types";

const audit = auditRaw as EvidenceAudit;
const KINDS: EvidenceKind[] = ["measured", "derived", "simulated", "narrative"];
const SCOPES: EvidenceScope[] = ["session", "scene", "profile", "research", "platform"];

function kindChip(kind: EvidenceKind) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded border border-surface-border px-2 py-1 font-mono text-[11px] text-foreground/55">
      <span className="grid h-5 w-5 place-items-center rounded-sm bg-white/[0.06] text-[11px]">
        {EVIDENCE_KIND_LETTER[kind]}
      </span>
      {EVIDENCE_KIND_LABEL[kind]}
    </span>
  );
}

export default function MethodAtlas() {
  const [query, setQuery] = useState("");
  const [kind, setKind] = useState<EvidenceKind | "all">("all");
  const [scope, setScope] = useState<EvidenceScope | "all">("all");
  const deferredQuery = useDeferredValue(query);

  const filtered = useMemo(() => {
    const needle = deferredQuery.trim().toLowerCase();
    return EVIDENCE_ENTRIES.filter((entry) => {
      if (kind !== "all" && entry.kind !== kind) return false;
      if (scope !== "all" && entry.scope !== scope) return false;
      if (!needle) return true;
      return `${entry.id} ${entry.label} ${entry.what} ${entry.method} ${entry.cannot} ${entry.surfaces.join(" ")}`
        .toLowerCase()
        .includes(needle);
    });
  }, [deferredQuery, kind, scope]);

  const affirmative = audit.findings.filter((finding) => !finding.negated);
  const boundary = audit.findings.filter((finding) => finding.negated);
  const pass = audit.status === "pass" && affirmative.length === 0 && audit.orphanIds.length === 0;

  return (
    <div className="mx-auto w-full max-w-[1320px] px-4 py-10 md:px-6">
      <PageHeader
        eyebrow="Method & Claim Atlas"
        title="Every number has a source. Every boundary has a link."
        description="A local, inspectable catalogue of the measurements, derived proxies, simulations, and narrative aids used by IMAGINA — including what each one cannot show."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <ClaimBadge />
            <GlassBoxToggle />
            <button
              type="button"
              onClick={() => window.print()}
              className="inline-flex h-11 items-center rounded-lg border border-surface-border px-3 text-[11px] text-foreground/60 hover:bg-white/[0.04] hover:text-foreground"
            >
              Print atlas
            </button>
          </div>
        }
      />

      <section className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {KINDS.map((item) => (
          <div key={item} className="rounded-xl border border-surface-border bg-white/[0.025] p-4">
            <div className="flex items-center justify-between gap-2">
              <span className="mono-label text-foreground/40">{EVIDENCE_KIND_LABEL[item]}</span>
              <span className="font-mono text-lg text-foreground/80">
                {EVIDENCE_ENTRIES.filter((entry) => entry.kind === item).length}
              </span>
            </div>
            <p className="mt-2 text-[11px] leading-5 text-foreground/45">{EVIDENCE_KIND_COPY[item]}</p>
          </div>
        ))}
      </section>

      <section className="mt-8 grid gap-4 lg:grid-cols-[1.35fr_0.65fr]">
        <Panel className="p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-base font-semibold">How to read a mark</h2>
              <p className="mt-1 text-sm leading-6 text-foreground/55">
                The letter is the evidence kind; colour and shape are redundant. Open a mark to see the source,
                method, uncertainty, and hard boundary.
              </p>
            </div>
            <span className="font-mono text-[11px] text-foreground/35">IMAGINA-EVIDENCE-REGISTRY-v1</span>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            {KINDS.map((item) => (
              <span key={item}>{kindChip(item)}</span>
            ))}
          </div>
          <div className="mt-4 grid gap-2 text-xs leading-5 text-foreground/50 sm:grid-cols-2">
            <p>
              <span className="text-foreground/75">Measured</span> — observed behaviour or self-report. Still not a
              clinical measurement.
            </p>
            <p>
              <span className="text-foreground/75">Derived</span> — computed from other values. The formula and its
              assumptions matter.
            </p>
            <p>
              <span className="text-foreground/75">Simulated</span> — synthetic. Useful for engineering checks, never
              human evidence.
            </p>
            <p>
              <span className="text-foreground/75">Narrative</span> — authored text or a symbolic aid. It is not a
              measurement.
            </p>
          </div>
        </Panel>

        <Panel className="p-5">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="text-base font-semibold">Static audit</h2>
              <p className="mt-1 text-sm leading-6 text-foreground/55">
                Scans JSX text for prohibited claims and verifies every evidence id used by the UI.
              </p>
            </div>
            <span
              className={`rounded-full border px-2.5 py-1 font-mono text-[11px] ${
                pass
                  ? "border-signal/30 bg-signal/[0.07] text-signal"
                  : "border-danger/35 bg-danger/[0.07] text-danger"
              }`}
            >
              {audit.status === "not_run" ? "not run" : pass ? "pass" : "fail"}
            </span>
          </div>
          <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
            <div>
              <dt className="mono-label text-foreground/35">Files</dt>
              <dd className="mt-1 font-mono text-foreground/75">{audit.filesScanned}</dd>
            </div>
            <div>
              <dt className="mono-label text-foreground/35">Entries</dt>
              <dd className="mt-1 font-mono text-foreground/75">{audit.entries}</dd>
            </div>
            <div>
              <dt className="mono-label text-foreground/35">Evidence ids used</dt>
              <dd className="mt-1 font-mono text-foreground/75">{audit.evidenceIdCount}</dd>
            </div>
            <div>
              <dt className="mono-label text-foreground/35">Orphans</dt>
              <dd className={`mt-1 font-mono ${audit.orphanIds.length ? "text-danger" : "text-foreground/75"}`}>
                {audit.orphanIds.length}
              </dd>
            </div>
          </dl>
          <p className="mt-4 font-mono text-[11px] leading-5 text-foreground/35">
            generatedAt: {audit.generatedAt ?? "never"}
          </p>
          <p className="mt-1 text-[11px] leading-5 text-foreground/40">
            {boundary.length} boundary / rejected-claim statements recognized; {affirmative.length} affirmative
            prohibited claims.
          </p>
          {audit.orphanIds.length ? (
            <p className="mt-2 break-words font-mono text-[11px] text-danger">Unknown: {audit.orphanIds.join(", ")}</p>
          ) : null}
        </Panel>
      </section>

      <section className="mt-8" aria-labelledby="atlas-entries-title">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 id="atlas-entries-title" className="text-lg font-semibold tracking-tight">
              Registry
            </h2>
            <p className="mt-1 text-sm text-foreground/50">
              {filtered.length} of {EVIDENCE_ENTRIES.length} entries. Anchor links are stable.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <label className="sr-only" htmlFor="atlas-query">
              Search evidence
            </label>
            <input
              id="atlas-query"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search id, method, boundary…"
              className="h-11 w-56 rounded-lg border border-surface-border bg-white/[0.03] px-3 text-sm outline-none placeholder:text-foreground/30 focus:border-signal/40"
            />
            <label className="sr-only" htmlFor="atlas-kind">
              Filter by evidence kind
            </label>
            <select
              id="atlas-kind"
              value={kind}
              onChange={(event) => setKind(event.target.value as EvidenceKind | "all")}
              className="h-11 rounded-lg border border-surface-border bg-[#090b14] px-3 text-sm text-foreground/70"
            >
              <option value="all">All kinds</option>
              {KINDS.map((item) => (
                <option key={item} value={item}>
                  {EVIDENCE_KIND_LABEL[item]}
                </option>
              ))}
            </select>
            <label className="sr-only" htmlFor="atlas-scope">
              Filter by scope
            </label>
            <select
              id="atlas-scope"
              value={scope}
              onChange={(event) => setScope(event.target.value as EvidenceScope | "all")}
              className="h-11 rounded-lg border border-surface-border bg-[#090b14] px-3 text-sm text-foreground/70"
            >
              <option value="all">All scopes</option>
              {SCOPES.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="mt-4 grid gap-3 lg:grid-cols-2">
          {filtered.map((entry) => (
            <article
              key={entry.id}
              id={entry.id.replaceAll(".", "-")}
              className="scroll-mt-24 rounded-xl border border-surface-border bg-white/[0.025] p-5"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-base font-semibold text-foreground/90">{entry.label}</h3>
                    {kindChip(entry.kind)}
                  </div>
                  <p className="mt-1 font-mono text-[11px] text-foreground/35">{entry.id}</p>
                </div>
                <span className="shrink-0 rounded border border-surface-border px-2 py-1 font-mono text-[11px] text-foreground/40">
                  {entry.tier}
                </span>
              </div>

              <p className="mt-3 text-sm leading-6 text-foreground/65">{entry.what}</p>

              <dl className="mt-4 space-y-3 border-t border-surface-border pt-4 text-xs leading-5">
                <div>
                  <dt className="mono-label text-foreground/35">Source</dt>
                  <dd className="mt-1 break-words font-mono text-[11px] text-signal/75">{entry.source}</dd>
                </div>
                <div>
                  <dt className="mono-label text-foreground/35">Method</dt>
                  <dd className="mt-1 text-foreground/55">{entry.method}</dd>
                </div>
                <div>
                  <dt className="mono-label text-foreground/35">Uncertainty</dt>
                  <dd className="mt-1 text-lock/75">{entry.uncertainty}</dd>
                </div>
                <div>
                  <dt className="mono-label text-danger/60">Cannot show</dt>
                  <dd className="mt-1 text-foreground/60">{entry.cannot}</dd>
                </div>
              </dl>

              <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-surface-border pt-3">
                {entry.surfaces.map((surface) => (
                  <span
                    key={surface}
                    className="rounded border border-surface-border px-2 py-1 font-mono text-[11px] text-foreground/40"
                  >
                    {surface}
                  </span>
                ))}
                {entry.studyEligible ? (
                  <Link
                    href={`/research/design?from=${encodeURIComponent(entry.id)}`}
                    className="ml-auto inline-flex min-h-9 items-center rounded-lg border border-signal/30 bg-signal/[0.07] px-3 text-[11px] text-signal hover:bg-signal/[0.12]"
                  >
                    Design a study
                  </Link>
                ) : null}
              </div>
            </article>
          ))}
        </div>

        {filtered.length === 0 ? (
          <div className="mt-4 rounded-xl border border-dashed border-surface-border p-10 text-center">
            <p className="text-sm text-foreground/50">No registered evidence matches those filters.</p>
            <button
              type="button"
              onClick={() => {
                setQuery("");
                setKind("all");
                setScope("all");
              }}
              className="mt-3 min-h-11 rounded-lg border border-surface-border px-4 text-sm text-foreground/65 hover:bg-white/[0.04]"
            >
              Clear filters
            </button>
          </div>
        ) : null}
      </section>

      {audit.findings.length ? (
        <details className="mt-8 rounded-xl border border-surface-border bg-white/[0.02] p-4">
          <summary className="cursor-pointer text-sm font-medium text-foreground/65">
            Audit contexts ({audit.findings.length})
          </summary>
          <ul className="mt-3 space-y-2 text-[11px] leading-5 text-foreground/45">
            {audit.findings.map((finding) => (
              <li key={`${finding.file}:${finding.line}:${finding.phrase}`} className="font-mono">
                <span className={finding.negated ? "text-signal/70" : "text-danger"}>
                  {finding.negated ? "boundary" : "affirmative"}
                </span>{" "}
                {finding.file}:{finding.line} · “{finding.phrase}” · {finding.text}
              </li>
            ))}
          </ul>
        </details>
      ) : null}

      <div className="mt-8">
        <BoundaryNote>
          The atlas documents local implementation and its limits. It is not a validation study, a clinical
          instrument, or evidence that IMAGINA improves mental imagery.
        </BoundaryNote>
      </div>

      <p className="mt-4 font-mono text-[11px] text-foreground/30">
        Registry reviewed {EVIDENCE_REGISTRY.reviewedAt} · {EVIDENCE_ENTRIES.length} entries
      </p>
    </div>
  );
}
