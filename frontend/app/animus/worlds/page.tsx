"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { useEffect, useState } from "react";
import AnimusShell from "@/components/animus/AnimusShell";
import Button from "@/components/common/Button";
import ButtonLink from "@/components/common/ButtonLink";
import HudLabel from "@/components/system/HudLabel";
import { IMAGINE_PRESETS } from "@/lib/imagine/presets";
import {
  deleteStudioWorld,
  listStudioWorlds,
  openStudioWorld,
  type StudioWorld,
} from "@/lib/animusStudioApi";
import { formatRelative } from "@/components/animus/sceneUtils";
import SceneSketch from "@/components/animus/SceneSketch";

export default function WorldsPage() {
  const router = useRouter();
  const [worlds, setWorlds] = useState<StudioWorld[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [confirmId, setConfirmId] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void listStudioWorlds(60)
      .then((result) => {
        if (!active) return;
        setWorlds(result.worlds);
        setError(null);
      })
      .catch((caught) => {
        if (!active) return;
        setError(caught instanceof Error ? caught.message : String(caught));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const open = async (world: StudioWorld) => {
    setBusyId(world.world_id);
    try {
      const session = await openStudioWorld(world.world_id);
      router.push(`/animus/studio/${session.session_id}`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
      setBusyId(null);
    }
  };

  const remove = async (world: StudioWorld) => {
    setBusyId(world.world_id);
    try {
      await deleteStudioWorld(world.world_id);
      setWorlds((current) => current.filter((item) => item.world_id !== world.world_id));
      setConfirmId(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setBusyId(null);
    }
  };

  return (
    <AnimusShell active="worlds">
      <div className="mx-auto w-full max-w-6xl px-6 py-10">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <div className="text-[11px] uppercase tracking-[0.22em] text-accent-glow/60">World library</div>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight">Saved worlds</h1>
            <p className="mt-2 max-w-xl text-xs leading-relaxed text-foreground/45">
              Every world is a complete scene graph you chose to keep. Open one to branch it into a new studio,
              or remove it from local storage.
            </p>
          </div>
          <ButtonLink href="/animus" size="sm" variant="secondary">← Back to Animus</ButtonLink>
        </div>

        <section className="mt-8" aria-labelledby="lumen-starters">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <HudLabel>Lumen starters</HudLabel>
              <h2 id="lumen-starters" className="mt-1 font-display text-xl text-foreground/90">
                Step into a composed world
              </h2>
            </div>
            <Link href="/animus/imagine" className="text-[11px] text-signal/70 hover:text-signal">
              Open the lab →
            </Link>
          </div>
          <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
            {IMAGINE_PRESETS.map((preset) => (
              <Link
                key={preset.id}
                href={`/animus/imagine?preset=${preset.id}`}
                className="group relative h-28 overflow-hidden rounded-lg border border-white/10 transition-colors hover:border-signal/35"
              >
                <span
                  className="absolute inset-0"
                  style={{
                    background: `radial-gradient(120% 110% at 20% 0%, ${preset.preview.via} 0%, ${preset.preview.from} 48%, ${preset.preview.to} 100%)`,
                  }}
                />
                <span className="absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-black/80 to-transparent" />
                <span
                  className="absolute left-3 top-3 h-1 w-7 rounded-full"
                  style={{ background: preset.preview.accent, boxShadow: `0 0 16px ${preset.preview.accent}` }}
                />
                <span className="absolute inset-x-0 bottom-0 p-3">
                  <span className="block truncate text-xs font-medium text-white/90">{preset.title}</span>
                  <span className="mt-0.5 block truncate font-mono text-[9px] uppercase tracking-[0.12em] text-white/40">
                    {preset.subtitle}
                  </span>
                </span>
              </Link>
            ))}
          </div>
        </section>

        {error && (
          <div role="alert" className="mt-6 rounded-lg border border-danger/25 bg-danger/10 px-3 py-2 text-[11px] text-red-200/80">
            {error}
          </div>
        )}

        {loading ? (
          <div className="mt-10 text-xs text-foreground/35">Loading local worlds…</div>
        ) : worlds.length === 0 ? (
          <div className="mt-10 rounded-2xl border border-dashed border-white/12 bg-white/[0.015] p-10 text-center">
            <h2 className="text-sm font-medium text-foreground/70">No saved worlds yet</h2>
            <p className="mx-auto mt-2 max-w-md text-[11px] leading-relaxed text-foreground/35">
              Build a scene in the studio, correct it until it fits, then choose “Save world”. It will appear here.
            </p>
            <ButtonLink href="/animus" size="sm" className="mt-4">
              Start a scene
            </ButtonLink>
          </div>
        ) : (
          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {worlds.map((world) => (
              <article
                key={world.world_id}
                className="group overflow-hidden rounded-xl border border-white/10 bg-white/[0.02] transition-colors hover:border-accent-glow/25"
              >
                <div className="relative h-28 overflow-hidden">
                  <SceneSketch scene={world.scene} className="absolute inset-0 h-full w-full" />
                  <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_25%,rgba(255,255,255,0.22),transparent_45%)]" />
                  <span className="absolute left-2.5 top-2 rounded bg-black/35 px-1.5 py-0.5 text-[11px] uppercase tracking-wider text-white/75 backdrop-blur">
                    {world.scene.style} · {world.scene.atmosphere.time_of_day}
                  </span>
                </div>
                <div className="space-y-2 p-3.5">
                  <h2 className="truncate text-sm font-medium text-foreground/85">{world.name}</h2>
                  <p className="line-clamp-2 min-h-[2.5em] text-[11px] leading-relaxed text-foreground/35">
                    {world.description || world.scene.title}
                  </p>
                  <div className="flex items-center justify-between text-[11px] text-foreground/25">
                    <span>{world.scene.entities.length} elements</span>
                    <span>{formatRelative(world.created_at)}</span>
                  </div>
                  <div className="flex gap-1.5 pt-1">
                    <Button
                      size="sm"
                      variant="secondary"
                      className="flex-1 text-[11px]"
                      disabled={busyId === world.world_id}
                      onClick={() => void open(world)}
                    >
                      {busyId === world.world_id ? "Opening…" : "Open studio"}
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      className={`text-[11px] ${
                        confirmId === world.world_id
                          ? "text-danger hover:text-danger"
                          : "text-danger/60 hover:text-danger"
                      }`}
                      disabled={busyId === world.world_id}
                      onClick={() => {
                        if (confirmId === world.world_id) void remove(world);
                        else setConfirmId(world.world_id);
                      }}
                      aria-label={
                        confirmId === world.world_id
                          ? `Confirm deleting ${world.name}`
                          : `Delete ${world.name}`
                      }
                    >
                      {busyId === world.world_id
                        ? "Deleting…"
                        : confirmId === world.world_id
                          ? "Confirm delete"
                          : "Delete"}
                    </Button>
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </AnimusShell>
  );
}
