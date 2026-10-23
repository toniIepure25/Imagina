"use client";

import { useState, type FormEvent } from "react";
import Button from "@/components/common/Button";
import type { SceneCommand, StudioSnapshot, StudioWorld } from "@/lib/animusStudioApi";
import HistoryPanel from "./HistoryPanel";
import {
  attrNumber,
  entityColor,
  entityKindLabel,
  isLocked,
  lockedAttributePaths,
} from "./sceneUtils";

const STYLES = ["cinematic", "minimal", "gothic", "surreal", "cyberpunk", "painterly", "ancient", "futuristic"];
const TIMES = ["dawn", "day", "dusk", "night"];
const WEATHERS = ["clear", "rain", "snow", "mist"];
const COLORS = ["#e14b4b", "#f2a65a", "#ffd27a", "#8fd694", "#6ec6ff", "#8b7cff", "#d78cff", "#e8e0cc", "#8a93a8", "#1a1830"];
const ADD_KINDS = [
  "castle", "moon", "tree", "mountain", "water", "cloud", "fire", "portal",
  "crystal", "person", "dragon", "building", "boat", "fog", "flower", "rock",
];

function RangeControl({
  label,
  value,
  min,
  max,
  step,
  disabled,
  onCommit,
  display,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  disabled: boolean;
  onCommit: (value: number) => void;
  display?: (value: number) => string;
}) {
  const [draft, setDraft] = useState<number | null>(null);
  const shown = draft ?? value;
  const commit = () => {
    if (draft !== null && Math.abs(draft - value) > 0.0001) onCommit(draft);
    setDraft(null);
  };
  return (
    <label className="block space-y-1">
      <span className="flex items-center justify-between text-[10px] text-foreground/45">
        <span>{label}</span>
        <span className="font-mono text-foreground/30">{display ? display(shown) : shown.toFixed(2)}</span>
      </span>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={shown}
        disabled={disabled}
        onChange={(event) => setDraft(Number(event.target.value))}
        onPointerUp={commit}
        onKeyUp={(event) => {
          if (["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) commit();
        }}
        onBlur={commit}
        className="h-1.5 w-full cursor-pointer appearance-none rounded-full bg-white/10 accent-[#79e8ff] disabled:opacity-40"
      />
    </label>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-2.5">
      <h3 className="text-[10px] uppercase tracking-[0.18em] text-foreground/40">{title}</h3>
      {children}
    </section>
  );
}

export default function InspectorPanel({
  snapshot,
  selectedId,
  busy,
  onSelect,
  onCommands,
  onUndo,
  onRedo,
  onBranch,
  onSwitchBranch,
  onSaveWorld,
}: {
  snapshot: StudioSnapshot;
  selectedId: string | null;
  busy: boolean;
  onSelect: (entityId: string | null) => void;
  onCommands: (commands: SceneCommand[], source?: string) => Promise<StudioSnapshot | null>;
  onUndo: () => Promise<unknown>;
  onRedo: () => Promise<unknown>;
  onBranch: (name?: string, fromVersionId?: string) => Promise<unknown>;
  onSwitchBranch: (branchId: string) => Promise<unknown>;
  onSaveWorld: (name: string, description: string) => Promise<StudioWorld | null>;
}) {
  const [tab, setTab] = useState<"scene" | "history">("scene");
  const [worldName, setWorldName] = useState<string | null>(null);
  const [worldDescription, setWorldDescription] = useState("");
  const [saving, setSaving] = useState(false);

  const scene = snapshot.scene;
  const effectiveWorldName = worldName ?? `${scene.title} world`;
  const selected = scene.entities.find((entity) => entity.id === selectedId) || null;
  const selectedLocked = selected ? isLocked(selected) : false;
  const lockedPaths = selected ? lockedAttributePaths(selected) : [];

  const save = async (event: FormEvent) => {
    event.preventDefault();
    if (!effectiveWorldName.trim() || saving) return;
    setSaving(true);
    await onSaveWorld(effectiveWorldName.trim(), worldDescription.trim());
    setSaving(false);
  };

  return (
    <div className="flex h-full flex-col">
      <div role="tablist" aria-label="Studio inspector" className="flex border-b border-surface-border">
        {(["scene", "history"] as const).map((item) => (
          <button
            key={item}
            type="button"
            role="tab"
            id={`inspector-tab-${item}`}
            aria-selected={tab === item}
            aria-controls={`inspector-panel-${item}`}
            tabIndex={tab === item ? 0 : -1}
            data-testid={`inspector-tab-${item}`}
            onClick={() => setTab(item)}
            onKeyDown={(event) => {
              if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
              event.preventDefault();
              const next =
                event.key === "Home"
                  ? "scene"
                  : event.key === "End"
                    ? "history"
                    : tab === "scene"
                      ? "history"
                      : "scene";
              setTab(next);
              document.getElementById(`inspector-tab-${next}`)?.focus();
            }}
            className={`flex-1 px-3 py-2.5 text-[10px] uppercase tracking-[0.18em] transition-colors ${
              tab === item
                ? "border-b border-accent-glow text-accent-glow"
                : "text-foreground/35 hover:text-foreground/60"
            }`}
          >
            {item}
          </button>
        ))}
      </div>

      <div
        role="tabpanel"
        id={`inspector-panel-${tab}`}
        aria-labelledby={`inspector-tab-${tab}`}
        className="flex-1 space-y-5 overflow-y-auto p-4"
      >
        {tab === "history" ? (
          <HistoryPanel
            versions={snapshot.history}
            branches={snapshot.branches}
            activeBranchId={snapshot.active_branch_id}
            activeVersionId={snapshot.active_version_id}
            hasUndo={snapshot.has_undo}
            hasRedo={snapshot.has_redo}
            busy={busy}
            onUndo={onUndo}
            onRedo={onRedo}
            onBranch={onBranch}
            onSwitchBranch={onSwitchBranch}
          />
        ) : (
          <>
            <Section title={`Elements · ${scene.entities.length}`}>
              <div className="max-h-40 space-y-1 overflow-y-auto pr-1">
                {scene.entities.length === 0 && (
                  <p className="text-[10px] text-foreground/30">No elements yet. Add one below.</p>
                )}
                {scene.entities.map((entity) => (
                  <button
                    key={entity.id}
                    type="button"
                    data-testid="entity-row"
                    onClick={() => onSelect(entity.id)}
                    className={`flex w-full items-center gap-2 rounded-md border px-2 py-1.5 text-left transition-colors ${
                      selected?.id === entity.id
                        ? "border-accent-glow/35 bg-accent-glow/[0.06]"
                        : "border-transparent hover:bg-white/[0.03]"
                    }`}
                  >
                    <span
                      className="h-2.5 w-2.5 shrink-0 rounded-full border border-white/25"
                      style={{ backgroundColor: entityColor(entity) }}
                    />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-[11px] text-foreground/70">{entity.label}</span>
                      <span className="block truncate text-[9px] text-foreground/25">
                        {entityKindLabel(entity.kind)} · {entity.role}
                      </span>
                    </span>
                    {isLocked(entity) && (
                      <span className="shrink-0 text-[9px] text-amber-200/60" title="Locked">
                        locked
                      </span>
                    )}
                  </button>
                ))}
              </div>
            </Section>

            {selected ? (
              <div className="space-y-3 rounded-lg border border-accent-glow/20 bg-accent-glow/[0.03] p-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <h3 className="truncate text-sm font-semibold text-foreground/90">{selected.label}</h3>
                    <p className="text-[10px] text-foreground/35">
                      {entityKindLabel(selected.kind)} · {selected.role} ·{" "}
                      {Math.round(selected.confidence * 100)}% confidence
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => onSelect(null)}
                    className="text-[10px] text-foreground/35 hover:text-foreground"
                  >
                    close
                  </button>
                </div>

                <div className="flex flex-wrap gap-1">
                  {COLORS.map((color) => (
                    <button
                      key={color}
                      type="button"
                      aria-label={`Set color ${color}`}
                      disabled={busy || selectedLocked || lockedPaths.includes("color")}
                      onClick={() =>
                        void onCommands([
                          { op: "set_entity_attribute", entity_id: selected.id, path: "color", value: color },
                        ])
                      }
                      className={`h-5 w-5 rounded-full border transition-transform hover:scale-110 disabled:opacity-35 ${
                        entityColor(selected) === color ? "border-white ring-1 ring-accent-glow" : "border-white/20"
                      }`}
                      style={{ backgroundColor: color }}
                    />
                  ))}
                  <label className="relative h-5 w-5 cursor-pointer overflow-hidden rounded-full border border-white/25 bg-[conic-gradient(red,yellow,lime,cyan,blue,magenta,red)]">
                    <input
                      type="color"
                      aria-label="Custom color"
                      disabled={busy || selectedLocked || lockedPaths.includes("color")}
                      value={entityColor(selected)}
                      onChange={(event) =>
                        void onCommands([
                          {
                            op: "set_entity_attribute",
                            entity_id: selected.id,
                            path: "color",
                            value: event.target.value,
                          },
                        ])
                      }
                      className="absolute inset-0 cursor-pointer opacity-0"
                    />
                  </label>
                </div>

                <RangeControl
                  label="Size"
                  value={attrNumber(selected, "size", 1)}
                  min={0.2}
                  max={4}
                  step={0.05}
                  disabled={busy || selectedLocked}
                  onCommit={(value) =>
                    void onCommands([
                      { op: "set_entity_attribute", entity_id: selected.id, path: "size", value },
                    ])
                  }
                />
                <RangeControl
                  label="Glow"
                  value={attrNumber(selected, "emissive", 0)}
                  min={0}
                  max={3}
                  step={0.05}
                  disabled={busy || selectedLocked}
                  onCommit={(value) =>
                    void onCommands([
                      { op: "set_entity_attribute", entity_id: selected.id, path: "emissive", value },
                    ])
                  }
                />

                <div className="flex flex-wrap gap-1.5">
                  <Button
                    size="sm"
                    variant={selected.locked ? "primary" : "secondary"}
                    disabled={busy}
                    onClick={() =>
                      void onCommands([{ op: "lock", entity_id: selected.id, locked: !selected.locked }])
                    }
                  >
                    {selected.locked ? "Unlock element" : "Lock element"}
                  </Button>
                  <Button
                    size="sm"
                    variant="secondary"
                    disabled={busy || !selected.attributes.color}
                    onClick={() =>
                      void onCommands([
                        {
                          op: "lock",
                          entity_id: selected.id,
                          path: "color",
                          locked: !lockedPaths.includes("color"),
                        },
                      ])
                    }
                  >
                    {lockedPaths.includes("color") ? "Unlock color" : "Lock color"}
                  </Button>
                </div>
                <button
                  type="button"
                  disabled={busy || selectedLocked}
                  onClick={() => {
                    void onCommands([{ op: "remove_entity", entity_id: selected.id }]);
                    onSelect(null);
                  }}
                  className="text-[10px] text-danger/60 hover:text-danger disabled:opacity-30"
                >
                  Remove this element
                </button>
              </div>
            ) : (
              <div className="rounded-lg border border-white/8 bg-white/[0.015] p-3 text-[11px] leading-relaxed text-foreground/40">
                Select an element in the scene to edit its color, size, glow, and locks. Locked elements are
                preserved by every regeneration.
              </div>
            )}

            <Section title="Atmosphere">
              <div className="grid grid-cols-2 gap-2">
                <label className="space-y-1 text-[10px] text-foreground/45">
                  <span>Style</span>
                  <select
                    value={scene.style}
                    disabled={busy}
                    onChange={(event) =>
                      void onCommands([{ op: "set_scene_attribute", path: "style", value: event.target.value }])
                    }
                    className="w-full rounded-md border border-white/10 bg-[#0c0f18] px-2 py-1.5 text-[11px] text-foreground/75 outline-none focus:border-accent-glow/40"
                  >
                    {STYLES.map((style) => (
                      <option key={style} value={style}>
                        {style}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="space-y-1 text-[10px] text-foreground/45">
                  <span>Time</span>
                  <select
                    value={scene.atmosphere.time_of_day}
                    disabled={busy}
                    onChange={(event) =>
                      void onCommands([
                        { op: "set_scene_attribute", path: "atmosphere.time_of_day", value: event.target.value },
                      ])
                    }
                    className="w-full rounded-md border border-white/10 bg-[#0c0f18] px-2 py-1.5 text-[11px] text-foreground/75 outline-none focus:border-accent-glow/40"
                  >
                    {TIMES.map((time) => (
                      <option key={time} value={time}>
                        {time}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="col-span-2 space-y-1 text-[10px] text-foreground/45">
                  <span>Weather</span>
                  <select
                    value={scene.atmosphere.weather}
                    disabled={busy}
                    onChange={(event) =>
                      void onCommands([
                        { op: "set_scene_attribute", path: "atmosphere.weather", value: event.target.value },
                      ])
                    }
                    className="w-full rounded-md border border-white/10 bg-[#0c0f18] px-2 py-1.5 text-[11px] text-foreground/75 outline-none focus:border-accent-glow/40"
                  >
                    {WEATHERS.map((weather) => (
                      <option key={weather} value={weather}>
                        {weather}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <RangeControl
                label="Fog"
                value={scene.atmosphere.fog.density}
                min={0}
                max={0.08}
                step={0.002}
                disabled={busy}
                onCommit={(value) =>
                  void onCommands([{ op: "set_scene_attribute", path: "atmosphere.fog.density", value }])
                }
                display={(value) => value.toFixed(3)}
              />
              <RangeControl
                label="Floating motion"
                value={scene.dynamics.floating}
                min={0}
                max={1}
                step={0.02}
                disabled={busy}
                onCommit={(value) =>
                  void onCommands([{ op: "set_scene_attribute", path: "dynamics.floating", value }])
                }
                display={(value) => `${Math.round(value * 100)}%`}
              />
              <RangeControl
                label="Key light"
                value={scene.lighting.key.intensity}
                min={0}
                max={5}
                step={0.05}
                disabled={busy}
                onCommit={(value) =>
                  void onCommands([{ op: "set_scene_attribute", path: "lighting.key.intensity", value }])
                }
              />
            </Section>

            <Section title="Add an element">
              <div className="flex flex-wrap gap-1">
                {ADD_KINDS.map((kind) => (
                  <button
                    key={kind}
                    type="button"
                    disabled={busy || scene.entities.length >= 40}
                    onClick={() => void onCommands([{ op: "add_entity", kind }])}
                    className="rounded-full border border-white/10 bg-white/[0.02] px-2 py-1 text-[10px] text-foreground/50 transition-colors hover:border-accent-glow/35 hover:text-foreground/85 disabled:opacity-30"
                  >
                    + {kind}
                  </button>
                ))}
              </div>
              <p className="text-[10px] leading-relaxed text-foreground/25">
                {scene.entities.length}/40 elements. Unknown kinds become abstract forms rather than failing.
              </p>
            </Section>

            <Section title="Keep this world">
              <form onSubmit={save} className="space-y-2">
                <input
                  value={effectiveWorldName}
                  onChange={(event) => setWorldName(event.target.value)}
                  maxLength={120}
                  placeholder="World name"
                  className="w-full rounded-md border border-white/10 bg-white/[0.03] px-2.5 py-1.5 text-[11px] outline-none placeholder:text-foreground/25 focus:border-accent-glow/40"
                />
                <textarea
                  value={worldDescription}
                  onChange={(event) => setWorldDescription(event.target.value)}
                  maxLength={500}
                  rows={2}
                  placeholder="Optional note about what makes this world yours"
                  className="w-full resize-none rounded-md border border-white/10 bg-white/[0.03] px-2.5 py-1.5 text-[11px] outline-none placeholder:text-foreground/25 focus:border-accent-glow/40"
                />
                <Button type="submit" size="sm" variant="secondary" disabled={busy || saving || !effectiveWorldName.trim()}>
                  {saving ? "Saving…" : "Save world"}
                </Button>
              </form>
            </Section>

            <div className="rounded-md border border-white/6 bg-white/[0.015] p-2.5 text-[9px] leading-relaxed text-foreground/25">
              Studio state is stored locally in SQLite. No image model, upload, or network call is used to
              render this scene. Claim ceiling: {snapshot.claim_label}.
            </div>
          </>
        )}
      </div>
    </div>
  );
}
