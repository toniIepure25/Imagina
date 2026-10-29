"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Button from "@/components/common/Button";
import {
  getStudioEvents,
  getStudioVersion,
  type StudioSnapshot,
  type StudioVersionDetail,
} from "@/lib/animusStudioApi";
import { errorMessage } from "@/lib/errors";
import { TRACE_BOUNDARY } from "@/lib/claims";
import {
  commandSummary,
  filterTraceEntries,
  mergeTraceEvents,
  traceTime,
  versionCommands,
  type TraceEntry,
  type TraceFilter,
} from "@/lib/tracebook";

const FILTERS: Array<{ id: TraceFilter; label: string }> = [
  { id: "all", label: "All" },
  { id: "intent", label: "Intent" },
  { id: "edits", label: "Edits" },
  { id: "candidates", label: "Candidates" },
  { id: "history", label: "History" },
];

const PAGE_SIZE = 200;
const MAX_INITIAL_PAGES = 5;

function kindLabel(entry: TraceEntry): string {
  if (entry.kind === "session") return "session";
  if (entry.kind === "intent") return "intent";
  if (entry.kind === "edit") return "edit";
  if (entry.kind === "candidate") return "candidate";
  if (entry.kind === "branch") return "branch";
  if (entry.kind === "world") return "world";
  if (entry.kind === "measurement") return "measure";
  return "history";
}

function formatPayload(payload: Record<string, unknown>): string {
  try {
    return JSON.stringify(payload, null, 2);
  } catch {
    return "{}";
  }
}

export default function TraceView({
  snapshot,
  previewVersionId,
  busy,
  onPreview,
}: {
  snapshot: StudioSnapshot;
  previewVersionId: string | null;
  busy: boolean;
  onPreview: (versionId: string) => void;
}) {
  const [entries, setEntries] = useState<TraceEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [filter, setFilter] = useState<TraceFilter>("all");
  const [query, setQuery] = useState("");
  const [selectedSeq, setSelectedSeq] = useState<number | null>(null);
  const [detail, setDetail] = useState<StudioVersionDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  const loadedUntilRef = useRef(0);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    loadedUntilRef.current = 0;

    const load = async () => {
      let after = 0;
      let collected: TraceEntry[] = [];
      let more = false;
      try {
        for (let page = 0; page < MAX_INITIAL_PAGES; page += 1) {
          const response = await getStudioEvents(snapshot.session_id, after, PAGE_SIZE);
          collected = mergeTraceEvents(collected, response.events);
          more = response.has_more;
          const last = response.events.at(-1)?.seq;
          if (!more || !last) break;
          after = last;
        }
        if (cancelled) return;
        loadedUntilRef.current = collected.at(-1)?.seq ?? 0;
        setEntries(collected);
        setHasMore(more);
        setSelectedSeq((current) => current ?? collected.at(-1)?.seq ?? null);
        setReady(true);
      } catch (caught) {
        if (cancelled) return;
        setError(errorMessage(caught, "The local event log could not be read."));
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    void load();
    return () => {
      cancelled = true;
    };
  }, [snapshot.session_id]);

  useEffect(() => {
    if (!ready || (snapshot.last_event_seq ?? 0) <= loadedUntilRef.current) return;
    let cancelled = false;
    const loadNew = async () => {
      try {
        const response = await getStudioEvents(snapshot.session_id, loadedUntilRef.current, PAGE_SIZE);
        if (cancelled) return;
        setEntries((current) => mergeTraceEvents(current, response.events));
        setHasMore(response.has_more);
        const last = response.events.at(-1)?.seq;
        if (last) loadedUntilRef.current = Math.max(loadedUntilRef.current, last);
        setSelectedSeq((current) => current ?? last ?? null);
      } catch {
        // The foreground snapshot remains usable; the next event or refresh retries.
      }
    };
    void loadNew();
    return () => {
      cancelled = true;
    };
  }, [ready, snapshot.last_event_seq, snapshot.session_id]);

  useEffect(() => {
    const versionId = entries.find((entry) => entry.seq === selectedSeq)?.versionId;
    if (!versionId) {
      return;
    }
    let cancelled = false;
    const timer = window.setTimeout(() => {
      setDetailLoading(true);
      setDetail(null);
      setDetailError(null);
      getStudioVersion(snapshot.session_id, versionId)
        .then((next) => {
          if (!cancelled) setDetail(next);
        })
        .catch((caught) => {
          if (!cancelled) {
            setDetail(null);
            setDetailError(errorMessage(caught, "This version detail is not available."));
          }
        })
        .finally(() => {
          if (!cancelled) setDetailLoading(false);
        });
    }, 0);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [entries, selectedSeq, snapshot.session_id]);

  const filtered = useMemo(() => filterTraceEntries(entries, filter, query), [entries, filter, query]);
  const selected = entries.find((entry) => entry.seq === selectedSeq) ?? null;

  const loadMore = async () => {
    const last = entries.at(-1)?.seq ?? 0;
    try {
      const response = await getStudioEvents(snapshot.session_id, last, PAGE_SIZE);
      setEntries((current) => mergeTraceEvents(current, response.events));
      setHasMore(response.has_more);
      if (response.events.at(-1)) loadedUntilRef.current = response.events.at(-1)!.seq;
    } catch (caught) {
      setError(errorMessage(caught, "Older events could not be loaded."));
    }
  };

  const moveSelection = (direction: number) => {
    if (!filtered.length) return;
    const index = filtered.findIndex((entry) => entry.seq === selectedSeq);
    const nextIndex = index < 0 ? (direction > 0 ? 0 : filtered.length - 1) : (index + direction + filtered.length) % filtered.length;
    setSelectedSeq(filtered[nextIndex].seq);
  };

  return (
    <div className="mx-auto grid w-full max-w-[1400px] gap-5 px-4 py-5 lg:grid-cols-[minmax(0,1fr)_390px] lg:px-6">
      <section aria-label="Event trace" className="min-w-0">
        <div className="flex flex-wrap items-end justify-between gap-3 border-b border-white/10 pb-4">
          <div>
            <p className="mono-label text-signal/75">Trace · read-only</p>
            <h2 className="mt-1 text-2xl font-semibold tracking-tight text-foreground">What the system did, in order</h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-foreground/55">
              One row per persisted event. Select a row to inspect the intent, the typed commands behind the version,
              and any parser warnings.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-[11px] text-foreground/40">
              {entries.length} event{entries.length === 1 ? "" : "s"}
            </span>
            <Button size="sm" variant="secondary" onClick={() => void loadMore()} disabled={!hasMore || loading}>
              Load older
            </Button>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <div role="group" aria-label="Filter events" className="flex flex-wrap items-center gap-1 rounded-lg border border-white/10 bg-white/[0.025] p-1">
            {FILTERS.map((item) => (
              <button
                key={item.id}
                type="button"
                aria-pressed={filter === item.id}
                data-testid={`trace-filter-${item.id}`}
                onClick={() => setFilter(item.id)}
                className={`min-h-8 rounded-md px-2.5 text-xs transition-colors ${
                  filter === item.id ? "bg-signal/12 text-signal" : "text-foreground/45 hover:text-foreground/80"
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>
          <label className="min-w-[190px] flex-1">
            <span className="sr-only">Search trace</span>
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search intent, event, or command…"
              className="min-h-9 w-full rounded-lg border border-white/10 bg-white/[0.025] px-3 text-sm text-foreground outline-none placeholder:text-foreground/30 focus:border-signal/40"
            />
          </label>
        </div>

        {loading ? (
          <div role="status" aria-busy="true" className="mt-4 space-y-2">
            {[0, 1, 2, 3].map((item) => (
              <div key={item} className="h-16 animate-pulse rounded-lg border border-white/8 bg-white/[0.025]" />
            ))}
          </div>
        ) : error ? (
          <div role="alert" className="mt-4 rounded-lg border border-danger/25 bg-danger/[0.06] p-4 text-sm text-red-200/85">
            <p className="font-medium">Trace unavailable</p>
            <p className="mt-1 text-red-100/60">{error}</p>
            <p className="mt-2 text-xs text-red-100/45">The Ledger still shows versions and branches.</p>
          </div>
        ) : filtered.length === 0 ? (
          <div role="status" className="mt-4 rounded-lg border border-white/8 bg-white/[0.025] p-6 text-sm text-foreground/50">
            {entries.length === 0
              ? "No persisted events yet. Make an edit or generate a candidate."
              : "No events match this filter. Clear the search or choose another lens."}
          </div>
        ) : (
          <div
            ref={listRef}
            role="listbox"
            aria-label="Studio events"
            data-testid="trace-list"
            tabIndex={0}
            aria-activedescendant={selected ? `trace-entry-${selected.seq}` : undefined}
            onKeyDown={(event) => {
              if (event.key === "ArrowDown") {
                event.preventDefault();
                moveSelection(1);
              } else if (event.key === "ArrowUp") {
                event.preventDefault();
                moveSelection(-1);
              } else if (event.key === "Home") {
                event.preventDefault();
                if (filtered[0]) setSelectedSeq(filtered[0].seq);
              } else if (event.key === "End") {
                event.preventDefault();
                if (filtered.at(-1)) setSelectedSeq(filtered.at(-1)!.seq);
              }
            }}
            className="mt-4 max-h-[62vh] overflow-y-auto rounded-xl border border-white/10 bg-[#080a0d]/60"
          >
            {filtered.map((entry) => {
              const active = entry.seq === selectedSeq;
              return (
                <div
                  key={entry.seq}
                  id={`trace-entry-${entry.seq}`}
                  data-testid={`trace-entry-${entry.seq}`}
                  role="option"
                  aria-selected={active}
                  tabIndex={-1}
                  onClick={() => setSelectedSeq(entry.seq)}
                  className={`grid cursor-pointer grid-cols-[62px_minmax(0,1fr)_auto] items-start gap-3 border-b border-white/[0.06] px-3 py-3 transition-colors last:border-b-0 ${
                    active ? "bg-signal/[0.075]" : "hover:bg-white/[0.03]"
                  }`}
                >
                  <div className="font-mono text-[11px] leading-5 text-foreground/35">
                    <div>#{entry.seq}</div>
                    <div>{traceTime(entry.createdAt)}</div>
                  </div>
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={`font-mono text-[11px] uppercase tracking-[0.12em] ${active ? "text-signal" : "text-foreground/35"}`}>
                        {kindLabel(entry)}
                      </span>
                      {entry.versionId ? (
                        <span className="rounded-full border border-white/10 px-2 py-0.5 font-mono text-[11px] text-foreground/40">
                          {entry.versionId.slice(-8)}
                        </span>
                      ) : null}
                      {entry.warnings.length ? (
                        <span className="rounded-full border border-lock/25 bg-lock/[0.08] px-2 py-0.5 font-mono text-[11px] text-lock/80">
                          {entry.warnings.length} warning{entry.warnings.length === 1 ? "" : "s"}
                        </span>
                      ) : null}
                    </div>
                    <div className="mt-1 truncate text-sm font-medium text-foreground/85">{entry.title}</div>
                    <div className="mt-0.5 truncate text-xs text-foreground/45">{entry.detail}</div>
                  </div>
                  <span className="mt-1 font-mono text-[11px] text-foreground/25" aria-hidden="true">
                    {active ? "◂" : ""}
                  </span>
                </div>
              );
            })}
            {hasMore ? (
              <button
                type="button"
                onClick={() => void loadMore()}
                className="w-full px-3 py-3 text-left text-xs text-signal/80 hover:bg-white/[0.03]"
              >
                Load older events →
              </button>
            ) : null}
          </div>
        )}
      </section>

      <aside aria-label="Selected event detail" data-testid="trace-detail" className="min-w-0 lg:sticky lg:top-4 lg:self-start">
        {selected ? (
          <div className="rounded-xl border border-white/10 bg-[#080a0d]/75">
            <div className="border-b border-white/8 p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="mono-label text-signal/75">{kindLabel(selected)} · #{selected.seq}</span>
                <span className="font-mono text-[11px] text-foreground/35">{traceTime(selected.createdAt)}</span>
              </div>
              <h3 className="mt-2 text-lg font-semibold text-foreground/90">{selected.title}</h3>
              <p className="mt-1 text-sm leading-6 text-foreground/50">{selected.detail}</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {selected.versionId ? (
                  <Button
                    size="sm"
                    variant="secondary"
                    disabled={busy}
                    onClick={() => onPreview(selected.versionId!)}
                  >
                    {previewVersionId === selected.versionId ? "Previewing this version" : "Preview this version"}
                  </Button>
                ) : null}
              </div>
            </div>

            <div className="space-y-4 p-4">
              {selected.intentText ? (
                <section>
                  <h4 className="mono-label text-foreground/40">Intent text</h4>
                  <p className="mt-1.5 text-sm leading-6 text-foreground/70">“{selected.intentText}”</p>
                </section>
              ) : null}

              {selected.resolutions.length ? (
                <section>
                  <h4 className="mono-label text-foreground/40">Resolutions</h4>
                  <ul className="mt-1.5 space-y-1 text-xs leading-5 text-foreground/60">
                    {selected.resolutions.map((item) => (
                      <li key={item}>· {item}</li>
                    ))}
                  </ul>
                </section>
              ) : null}

              {selected.warnings.length ? (
                <section>
                  <h4 className="mono-label text-lock/70">Parser warnings</h4>
                  <ul className="mt-1.5 space-y-1 text-xs leading-5 text-lock/80">
                    {selected.warnings.map((item) => (
                      <li key={item}>· {item}</li>
                    ))}
                  </ul>
                </section>
              ) : null}

              {selected.versionId ? (
                <section>
                  <h4 className="mono-label text-foreground/40">Typed commands</h4>
                  {detailLoading ? (
                    <p className="mt-1.5 text-xs text-foreground/40">Reading version detail…</p>
                  ) : detailError ? (
                    <p className="mt-1.5 text-xs text-foreground/45">{detailError}</p>
                  ) : versionCommands(detail).length ? (
                    <ol className="mt-1.5 space-y-1.5">
                      {versionCommands(detail).map((command, index) => (
                        <li key={`${command.op}-${index}`} className="rounded-md border border-white/8 bg-white/[0.02] px-2.5 py-1.5 text-xs text-foreground/60">
                          <span className="mr-1.5 font-mono text-[11px] text-foreground/30">{index + 1}.</span>
                          {commandSummary(command)}
                        </li>
                      ))}
                    </ol>
                  ) : (
                    <p className="mt-1.5 text-xs text-foreground/40">No typed commands were recorded for this version.</p>
                  )}
                </section>
              ) : null}

              <details className="rounded-md border border-white/8 bg-white/[0.02] p-2.5">
                <summary className="cursor-pointer text-xs text-foreground/45">Raw event payload</summary>
                <pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap font-mono text-[11px] leading-5 text-foreground/40">
                  {formatPayload(selected.payload)}
                </pre>
              </details>

              <p className="border-t border-white/8 pt-3 text-[11px] leading-5 text-foreground/35">{TRACE_BOUNDARY}</p>
            </div>
          </div>
        ) : (
          <div className="rounded-xl border border-white/8 bg-white/[0.025] p-4 text-sm text-foreground/45">
            Select an event to inspect its intent and commands.
          </div>
        )}
      </aside>
    </div>
  );
}
