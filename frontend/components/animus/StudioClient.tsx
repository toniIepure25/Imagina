"use client";

import Link from "next/link";
import { useState } from "react";
import Header from "@/components/layout/Header";
import Button from "@/components/common/Button";
import CandidateStrip from "@/components/animus/CandidateStrip";
import InspectorPanel from "@/components/animus/InspectorPanel";
import PromptBar from "@/components/animus/PromptBar";
import AnimusScene from "@/components/animus/AnimusScene";
import { useAnimusStudio } from "@/lib/useAnimusStudio";
import type { StudioApiError } from "@/lib/animusStudioApi";

function loadErrorCopy(error: StudioApiError | null): { title: string; body: string } {
  if (error?.status === 404) {
    return {
      title: "This studio does not exist",
      body: "The session may have been deleted, or the link is wrong. You can start a new scene or open a saved world.",
    };
  }
  if (error?.status === 503 || error?.code === "corrupt_local_state") {
    return {
      title: "The local Studio database is unavailable",
      body: error?.detail || "Back up the local database and try again once the backend is healthy.",
    };
  }
  if (error?.status === 0) {
    return {
      title: "The local backend is not reachable",
      body: error?.detail || "Start the backend, then try again.",
    };
  }
  return {
    title: "This studio could not be opened",
    body: error?.detail || "The session does not exist or the local backend is unavailable.",
  };
}

export default function StudioClient({ sessionId }: { sessionId: string }) {
  const studio = useAnimusStudio(sessionId);
  const [rawSelectedId, setRawSelectedId] = useState<string | null>(null);
  const [savingWorld, setSavingWorld] = useState(false);

  const snapshot = studio.snapshot;
  const selectedId =
    rawSelectedId && snapshot?.scene.entities.some((entity) => entity.id === rawSelectedId)
      ? rawSelectedId
      : null;
  const failure = loadErrorCopy(studio.loadError);

  if (studio.loading && !snapshot) {
    return (
      <div className="flex min-h-screen flex-col">
        <Header status="local" />
        <main className="flex flex-1 items-center justify-center" aria-busy="true">
          <div className="space-y-3 text-center">
            <div className="mx-auto h-9 w-9 animate-spin rounded-full border-2 border-accent-glow/20 border-t-accent-glow" />
            <p className="text-xs text-foreground/40" role="status">Opening your studio…</p>
          </div>
        </main>
      </div>
    );
  }

  if (!snapshot) {
    return (
      <div className="flex min-h-screen flex-col">
        <Header status="local" />
        <main className="flex flex-1 items-center justify-center p-6">
          <div className="glass max-w-md space-y-4 p-6 text-center" role="alert">
            <h1 className="text-lg font-semibold">{failure.title}</h1>
            <p className="text-xs leading-relaxed text-foreground/50">{failure.body}</p>
            <div className="flex justify-center gap-2">
              <Button size="sm" variant="secondary" onClick={() => void studio.reload()}>
                Try again
              </Button>
              <Link href="/animus">
                <Button size="sm">Back to Animus</Button>
              </Link>
            </div>
          </div>
        </main>
      </div>
    );
  }

  const saveWorld = async () => {
    if (savingWorld) return;
    setSavingWorld(true);
    await studio.saveWorld(`${snapshot.title} world`, "");
    setSavingWorld(false);
  };

  return (
    <div className="flex min-h-screen flex-col">
      <Header status={studio.connected ? "live" : "local"} />
      <main className="flex flex-1 flex-col xl:grid xl:h-[calc(100vh-57px)] xl:grid-cols-[minmax(0,1fr)_370px] xl:overflow-hidden">
        <section className="flex min-h-0 flex-1 flex-col">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-surface-border bg-background/70 px-4 py-2">
            <div className="flex min-w-0 items-center gap-3">
              <Link href="/animus" className="shrink-0 text-[10px] text-foreground/40 hover:text-foreground">
                ← Animus
              </Link>
              <div className="min-w-0">
                <h1 className="truncate text-sm font-semibold text-foreground/90">{snapshot.title}</h1>
                <div className="flex items-center gap-2 text-[9px] text-foreground/35">
                  <span data-testid="studio-version">v{snapshot.version.number}</span>
                  <span>·</span>
                  <span data-testid="studio-branch">{snapshot.active_branch_name}</span>
                  <span>·</span>
                  <span>{snapshot.history.length} versions</span>
                  <span>·</span>
                  <span data-testid="studio-connection" className="inline-flex items-center gap-1">
                    <span
                      className={`h-1.5 w-1.5 rounded-full ${studio.connected ? "bg-emerald-400" : "bg-foreground/25"}`}
                    />
                    {studio.connected ? "live" : "local"}
                  </span>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="hidden rounded-full border border-accent-glow/25 bg-accent-glow/5 px-2 py-1 text-[9px] text-accent-glow/75 sm:inline">
                L1 · behavioral-assisted
              </span>
              <Button
                size="sm"
                variant="ghost"
                disabled={studio.busy || !snapshot.has_undo}
                onClick={() => void studio.undo()}
                className="text-[10px]"
              >
                Undo
              </Button>
              <Button
                size="sm"
                variant="ghost"
                disabled={studio.busy || !snapshot.has_redo}
                onClick={() => void studio.redo()}
                className="text-[10px]"
              >
                Redo
              </Button>
              <Button
                size="sm"
                variant="secondary"
                disabled={studio.busy || savingWorld}
                onClick={() => void saveWorld()}
                className="text-[10px]"
              >
                {savingWorld ? "Saving…" : "Save world"}
              </Button>
            </div>
          </div>

          <AnimusScene
            scene={snapshot.scene}
            selectedId={selectedId}
            onSelect={setRawSelectedId}
            className="min-h-[48vh] flex-1 xl:min-h-0"
          />
          <CandidateStrip
            candidates={snapshot.candidates}
            activeHash={snapshot.scene.metadata.content_hash ?? ""}
            busy={studio.busy}
            onSelect={studio.selectCandidate}
            onRegenerate={() => studio.regenerate([])}
          />
          <PromptBar
            busy={studio.busy}
            notice={studio.notice}
            onSubmit={studio.refine}
            onClearNotice={studio.clearNotice}
          />
        </section>

        <aside className="min-h-0 border-t border-surface-border bg-[#080a12]/70 xl:border-l xl:border-t-0">
          <InspectorPanel
            snapshot={snapshot}
            selectedId={selectedId}
            busy={studio.busy}
            onSelect={setRawSelectedId}
            onCommands={studio.commands}
            onUndo={studio.undo}
            onRedo={studio.redo}
            onBranch={studio.branch}
            onSwitchBranch={studio.switchBranch}
            onSaveWorld={studio.saveWorld}
          />
        </aside>
      </main>
    </div>
  );
}
