import type { SceneCommand, StudioEvent, StudioVersionDetail } from "@/lib/animusStudioApi";

export type TraceFilter = "all" | "intent" | "edits" | "candidates" | "history";

export type TraceKind = "session" | "intent" | "edit" | "candidate" | "history" | "branch" | "world" | "measurement" | "other";

export interface TraceEntry {
  seq: number;
  eventType: string;
  kind: TraceKind;
  title: string;
  detail: string;
  versionId: string | null;
  createdAt: string;
  intentText: string | null;
  warnings: string[];
  resolutions: string[];
  payload: Record<string, unknown>;
}

const KIND_BY_EVENT: Record<string, TraceKind> = {
  "studio.session.created": "session",
  "studio.intent.applied": "intent",
  "studio.commands.applied": "edit",
  "studio.candidates.generated": "candidate",
  "studio.candidate.selected": "candidate",
  "studio.undo": "history",
  "studio.redo": "history",
  "studio.branch.created": "branch",
  "studio.branch.switched": "branch",
  "studio.world.saved": "world",
  "studio.trial.recorded": "measurement",
  "studio.interview.probe_recorded": "measurement",
  "studio.contrast.trial_recorded": "measurement",
};

const FILTER_KINDS: Record<Exclude<TraceFilter, "all">, TraceKind[]> = {
  intent: ["intent"],
  edits: ["edit", "candidate"],
  candidates: ["candidate"],
  history: ["history", "branch", "world", "session"],
};

function strings(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

function text(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function count(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function versionFrom(event: StudioEvent): string | null {
  return (
    event.version_id ??
    text(event.payload.version_id) ??
    text(event.payload.source_version_id) ??
    text(event.payload.from_version_id)
  );
}

export function normalizeTraceEvent(event: StudioEvent): TraceEntry {
  const kind = KIND_BY_EVENT[event.event_type] ?? "other";
  const payload = event.payload;
  const versionId = versionFrom(event);
  const intentText = text(payload.text) ?? text(payload.intention);
  const warnings = strings(payload.warnings);
  const resolutions = strings(payload.resolutions);
  const base = {
    seq: event.seq,
    eventType: event.event_type,
    kind,
    versionId,
    createdAt: event.created_at,
    intentText,
    warnings,
    resolutions,
    payload,
  };

  switch (event.event_type) {
    case "studio.session.created": {
      const title = text(payload.title) ?? "Untitled studio";
      return {
        ...base,
        title: "Session created",
        detail: intentText ? `${title} · ${intentText}` : title,
      };
    }
    case "studio.intent.applied":
      return {
        ...base,
        title: "Intent applied",
        detail: intentText ?? "A natural-language intention produced a new version.",
      };
    case "studio.commands.applied": {
      const commands = Array.isArray(payload.commands) ? payload.commands.length : 0;
      return {
        ...base,
        title: commands === 1 ? "Manual edit applied" : "Manual edits applied",
        detail: commands ? `${commands} typed command${commands === 1 ? "" : "s"}` : "Typed commands produced a new version.",
      };
    }
    case "studio.candidates.generated": {
      const generated = count(payload.count) ?? (Array.isArray(payload.candidate_ids) ? payload.candidate_ids.length : 0);
      return {
        ...base,
        title: generated === 1 ? "Candidate generated" : "Candidates generated",
        detail: generated
          ? `${generated} candidate${generated === 1 ? "" : "s"} from this head`
          : "A new candidate set was generated.",
      };
    }
    case "studio.candidate.selected": {
      const variant = count(payload.variant_index);
      return {
        ...base,
        title: "Candidate kept",
        detail: variant === null ? "A candidate became the new head." : `Variant ${variant + 1} became the new head.`,
      };
    }
    case "studio.undo":
      return { ...base, title: "Undo", detail: "The branch head moved back one version." };
    case "studio.redo":
      return { ...base, title: "Redo", detail: "The branch head moved forward one version." };
    case "studio.branch.created": {
      const name = text(payload.name) ?? "New branch";
      return { ...base, title: "Branch created", detail: `${name} · forked from an earlier version.` };
    }
    case "studio.branch.switched": {
      const branch = text(payload.branch_id) ?? "another branch";
      return { ...base, title: "Branch switched", detail: `Active branch: ${branch}.` };
    }
    case "studio.world.saved": {
      const name = text(payload.name) ?? "Saved world";
      const items = count(payload.items);
      return {
        ...base,
        title: "World saved",
        detail: items === null ? name : `${name} · ${items} element${items === 1 ? "" : "s"}`,
      };
    }
    default:
      return {
        ...base,
        title: humanizeEventType(event.event_type),
        detail: "Recorded by the local Studio event log.",
      };
  }
}

export function humanizeEventType(eventType: string): string {
  const stripped = eventType.replace(/^studio\./, "").replaceAll("_", " ").replaceAll(".", " · ");
  return stripped.charAt(0).toUpperCase() + stripped.slice(1);
}

export function normalizeTraceEvents(events: StudioEvent[]): TraceEntry[] {
  const bySeq = new Map<number, TraceEntry>();
  for (const event of events) {
    if (!Number.isFinite(event.seq)) continue;
    bySeq.set(event.seq, normalizeTraceEvent(event));
  }
  return [...bySeq.values()].sort((a, b) => a.seq - b.seq);
}

export function mergeTraceEvents(current: TraceEntry[], incoming: StudioEvent[]): TraceEntry[] {
  const bySeq = new Map<number, TraceEntry>();
  for (const entry of current) bySeq.set(entry.seq, entry);
  for (const event of incoming) bySeq.set(event.seq, normalizeTraceEvent(event));
  return [...bySeq.values()].sort((a, b) => a.seq - b.seq);
}

export function filterTraceEntries(entries: TraceEntry[], filter: TraceFilter, query: string): TraceEntry[] {
  const needle = query.trim().toLowerCase();
  const kinds = filter === "all" ? null : FILTER_KINDS[filter];
  return entries.filter((entry) => {
    if (kinds && !kinds.includes(entry.kind)) return false;
    if (!needle) return true;
    return `${entry.title} ${entry.detail} ${entry.eventType} ${entry.intentText ?? ""}`
      .toLowerCase()
      .includes(needle);
  });
}

export function traceTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "--:--:--";
  return date.toLocaleTimeString(undefined, { hour12: false });
}

export function commandSummary(command: SceneCommand): string {
  switch (command.op) {
    case "add_entity":
      return `Add ${command.label || command.kind || "element"}`;
    case "remove_entity":
      return `Remove ${command.entity_id}`;
    case "set_entity_attribute":
      return `Set ${command.entity_id}.${command.path}`;
    case "set_entity_transform":
      return `Transform ${command.entity_id}`;
    case "lock":
      return `${command.locked ? "Lock" : "Unlock"} ${command.entity_id ?? command.path ?? "element"}`;
    case "set_scene_attribute":
      return `Set scene.${command.path}`;
    case "set_relation":
      return `Relate ${command.subject_id} ${command.relation} ${command.object_id}`;
    case "remove_relation":
      return `Remove relation ${command.subject_id} ${command.relation} ${command.object_id}`;
    default:
      return "Scene command";
  }
}

export function versionCommands(detail: StudioVersionDetail | null): SceneCommand[] {
  return detail?.commands ?? [];
}
