"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import AppShell from "@/components/layout/AppShell";
import Button from "@/components/common/Button";
import {
  deleteStudioWorld,
  listStudioWorlds,
  openStudioWorld,
  type StudioWorld,
} from "@/lib/animusStudioApi";
import { formatRelative, sceneGradient } from "@/components/animus/sceneUtils";

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
    <AppShell>
      <div className="mx-auto w-full max-w-6xl px-6 py-10">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <div className="text-[10px] uppercase tracking-[0.22em] text-accent-glow/60">World library</div>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight">Saved worlds</h1>
            <p className="mt-2 max-w-xl text-xs leading-relaxed text-foreground/45">
              Every world is a complete scene graph you chose to keep. Open one to branch it into a new studio,
              or remove it from local storage.
            </p>
          </div>
          <Link href="/animus">
            <Button size="sm" variant="secondary">← Back to Animus</Button>
          </Link>
        </div>

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
            <Link href="/animus" className="mt-4 inline-block">
              <Button size="sm">Start a scene</Button>
            </Link>
          </div>
        ) : (
          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {worlds.map((world) => (
              <article
                key={world.world_id}
                className="group overflow-hidden rounded-xl border border-white/10 bg-white/[0.02] transition-colors hover:border-accent-glow/25"
              >
                <div className="relative h-28" style={{ background: sceneGradient(world.scene) }}>
                  <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_25%,rgba(255,255,255,0.22),transparent_45%)]" />
                  <span className="absolute left-2.5 top-2 rounded bg-black/35 px-1.5 py-0.5 text-[9px] uppercase tracking-wider text-white/75 backdrop-blur">
                    {world.scene.style} · {world.scene.atmosphere.time_of_day}
                  </span>
                </div>
                <div className="space-y-2 p-3.5">
                  <h2 className="truncate text-sm font-medium text-foreground/85">{world.name}</h2>
                  <p className="line-clamp-2 min-h-[2.5em] text-[11px] leading-relaxed text-foreground/35">
                    {world.description || world.scene.title}
                  </p>
                  <div className="flex items-center justify-between text-[9px] text-foreground/25">
                    <span>{world.scene.entities.length} elements</span>
                    <span>{formatRelative(world.created_at)}</span>
                  </div>
                  <div className="flex gap-1.5 pt-1">
                    <Button
                      size="sm"
                      variant="secondary"
                      className="flex-1 text-[10px]"
                      disabled={busyId === world.world_id}
                      onClick={() => void open(world)}
                    >
                      {busyId === world.world_id ? "Opening…" : "Open studio"}
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      className={`text-[10px] ${
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
    </AppShell>
  );
}
