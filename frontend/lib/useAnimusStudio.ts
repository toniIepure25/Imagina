"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  StudioApiError,
  applyStudioCommands,
  applyStudioIntent,
  createStudioBranch,
  getStudioSession,
  parseStudioWebSocketMessage,
  redoStudio,
  regenerateStudio,
  saveStudioWorld,
  selectStudioCandidate,
  studioWebSocketUrl,
  switchStudioBranch,
  undoStudio,
  type SceneCommand,
  type StudioCandidate,
  type StudioSnapshot,
  type StudioWorldSaveResult,
} from "@/lib/animusStudioApi";

export interface StudioNotice {
  kind: "info" | "success" | "error";
  text: string;
}

function messageOf(error: unknown): string {
  if (error instanceof StudioApiError) {
    if (error.code === "timeout") return error.detail;
    if (error.code === "stale_version") return "The scene changed in another view. Refreshing the latest state.";
    return error.detail;
  }
  if (error instanceof Error) return error.message;
  return String(error);
}

export function useAnimusStudio(sessionId: string) {
  const [snapshot, setSnapshot] = useState<StudioSnapshot | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [connected, setConnected] = useState(false);
  const [notice, setNotice] = useState<StudioNotice | null>(null);
  const [loadError, setLoadError] = useState<StudioApiError | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const heartbeatRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const refreshTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const closedRef = useRef(false);
  const attemptRef = useRef(0);
  const busyRef = useRef(false);
  const snapshotRef = useRef<StudioSnapshot | null>(null);
  const loadSeqRef = useRef(0);
  const mutationSeqRef = useRef(0);
  const lastEventSeqRef = useRef(0);
  const lastMessageAtRef = useRef(0);
  const mutationAbortRef = useRef<AbortController | null>(null);

  const applySnapshot = useCallback((next: StudioSnapshot): boolean => {
    const nextSeq = next.last_event_seq ?? 0;
    if (nextSeq > 0 && nextSeq < lastEventSeqRef.current) return false;
    if (nextSeq > 0) lastEventSeqRef.current = nextSeq;
    snapshotRef.current = next;
    setSnapshot(next);
    return true;
  }, []);

  const load = useCallback(
    async (quiet = false, signal?: AbortSignal) => {
      const seq = ++loadSeqRef.current;
      if (!quiet) setLoading(true);
      try {
        const next = await getStudioSession(sessionId, { signal });
        if (signal?.aborted || seq !== loadSeqRef.current || busyRef.current) return;
        if (!applySnapshot(next)) return;
        setLoadError(null);
        if (!quiet) setNotice(null);
      } catch (error) {
        if (signal?.aborted || seq !== loadSeqRef.current) return;
        const typed =
          error instanceof StudioApiError
            ? error
            : new StudioApiError(0, messageOf(error), "unknown_error");
        setLoadError(typed);
        if (!quiet) setNotice({ kind: "error", text: messageOf(error) });
      } finally {
        if (seq === loadSeqRef.current && !quiet) setLoading(false);
      }
    },
    [applySnapshot, sessionId],
  );

  useEffect(() => {
    lastEventSeqRef.current = 0;
    lastMessageAtRef.current = 0;
    mutationAbortRef.current?.abort();
    mutationAbortRef.current = null;
    mutationSeqRef.current += 1;
    busyRef.current = false;
    const timer = window.setTimeout(() => setBusy(false), 0);
    return () => window.clearTimeout(timer);
  }, [sessionId]);

  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      void load(false, controller.signal);
    }, 0);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [load]);

  useEffect(() => {
    return () => {
      mutationAbortRef.current?.abort();
      mutationAbortRef.current = null;
    };
  }, []);

  useEffect(() => {
    closedRef.current = false;
    attemptRef.current = 0;

    const clearTimers = () => {
      if (heartbeatRef.current) clearInterval(heartbeatRef.current);
      if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
      heartbeatRef.current = null;
      refreshTimerRef.current = null;
    };

    const connect = () => {
      if (closedRef.current) return;
      let socket: WebSocket;
      try {
        socket = new WebSocket(studioWebSocketUrl(sessionId));
      } catch {
        setConnected(false);
        return;
      }
      socketRef.current = socket;

      socket.onopen = () => {
        attemptRef.current = 0;
        lastMessageAtRef.current = Date.now();
        setConnected(true);
        if (heartbeatRef.current) clearInterval(heartbeatRef.current);
        heartbeatRef.current = setInterval(() => {
          if (Date.now() - lastMessageAtRef.current > 60_000) {
            socket.close();
            return;
          }
          if (socket.readyState === WebSocket.OPEN) {
            try {
              socket.send(JSON.stringify({ type: "ping" }));
            } catch {
              socket.close();
            }
          }
        }, 25_000);
      };

      socket.onclose = () => {
        setConnected(false);
        if (heartbeatRef.current) clearInterval(heartbeatRef.current);
        heartbeatRef.current = null;
        if (closedRef.current) return;
        const delay = Math.min(1_000 * 2 ** attemptRef.current, 15_000) + Math.random() * 300;
        attemptRef.current += 1;
        reconnectRef.current = setTimeout(connect, delay);
      };

      socket.onerror = () => {
        setConnected(false);
      };

      socket.onmessage = (event) => {
        lastMessageAtRef.current = Date.now();
        try {
          const payload = parseStudioWebSocketMessage(JSON.parse(event.data));
          if (!payload) return;
          if (payload.type === "snapshot" && !busyRef.current) {
            loadSeqRef.current += 1;
            setLoading(false);
            if (applySnapshot(payload.session)) setLoadError(null);
            return;
          }
          if (payload.type === "resync_required") {
            if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
            refreshTimerRef.current = setTimeout(() => {
              if (!busyRef.current) void load(true);
            }, 0);
            return;
          }
          if (payload.type === "error") {
            setNotice({ kind: "error", text: payload.message || payload.code });
            return;
          }
          if (payload.type === "event" && !busyRef.current) {
            const seq = typeof payload.seq === "number" ? payload.seq : null;
            let gap = false;
            if (seq !== null) {
              if (seq <= lastEventSeqRef.current) return;
              gap = seq > lastEventSeqRef.current + 1;
              lastEventSeqRef.current = seq;
            }
            if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
            refreshTimerRef.current = setTimeout(() => {
              if (!busyRef.current) void load(true);
            }, gap ? 0 : 120);
          }
        } catch {
          /* ignore malformed local events */
        }
      };
    };

    connect();
    return () => {
      closedRef.current = true;
      clearTimers();
      if (reconnectRef.current) clearTimeout(reconnectRef.current);
      reconnectRef.current = null;
      socketRef.current?.close();
      socketRef.current = null;
    };
  }, [applySnapshot, load, sessionId]);

  const run = useCallback(
    async (
      operation: (signal: AbortSignal) => Promise<StudioSnapshot>,
      success?: (next: StudioSnapshot) => StudioNotice | null,
    ) => {
      mutationAbortRef.current?.abort();
      const controller = new AbortController();
      mutationAbortRef.current = controller;
      const seq = ++mutationSeqRef.current;
      busyRef.current = true;
      setBusy(true);
      setNotice(null);
      try {
        const next = await operation(controller.signal);
        if (controller.signal.aborted || seq !== mutationSeqRef.current) return null;
        if (!applySnapshot(next)) return null;
        if (success) {
          const nextNotice = success(next);
          if (nextNotice) setNotice(nextNotice);
        }
        return next;
      } catch (error) {
        if (controller.signal.aborted || seq !== mutationSeqRef.current) return null;
        setNotice({ kind: "error", text: messageOf(error) });
        if (error instanceof StudioApiError && error.code === "stale_version") {
          setTimeout(() => void load(true), 0);
        }
        return null;
      } finally {
        if (seq === mutationSeqRef.current) {
          mutationAbortRef.current = null;
          busyRef.current = false;
          setBusy(false);
        }
      }
    },
    [applySnapshot, load],
  );

  const refine = useCallback(
    (text: string) =>
      run(
        (signal) =>
          applyStudioIntent(sessionId, text, {
            expectedVersion: snapshotRef.current?.active_version_id,
            signal,
          }),
        (next) => {
          if (next.needs_clarification) {
            return {
              kind: "info",
              text: next.clarification || "I could not turn that into a scene change yet.",
            };
          }
          const resolutions = next.resolutions?.length ? next.resolutions.join(" · ") : "Scene updated";
          return { kind: "success", text: resolutions };
        },
      ),
    [run, sessionId],
  );

  const regenerate = useCallback(
    (locks: string[] = [], options: { count?: number; strength?: number } = {}) =>
      run(
        (signal) =>
          regenerateStudio(
            sessionId,
            { ...options, locks },
            { expectedVersion: snapshotRef.current?.active_version_id, signal },
          ),
        (next) => {
          const count = next.generated?.length ?? 0;
          return {
            kind: "success",
            text: count
              ? `${count} candidate${count === 1 ? "" : "s"} generated. Pick one to keep.`
              : "No new visible candidates for this scene. Keep an earlier choice or change the scene.",
          };
        },
      ),
    [run, sessionId],
  );

  const selectCandidate = useCallback(
    (candidate: StudioCandidate) =>
      run(
        (signal) =>
          selectStudioCandidate(sessionId, candidate.candidate_id, {
            expectedVersion: snapshotRef.current?.active_version_id,
            signal,
          }),
        () => ({ kind: "success", text: "Candidate kept as a new version." }),
      ),
    [run, sessionId],
  );

  const commands = useCallback(
    (batch: SceneCommand[], sourceText = "manual edit") =>
      run((signal) =>
        applyStudioCommands(sessionId, batch, sourceText, {
          expectedVersion: snapshotRef.current?.active_version_id,
          signal,
        }),
      ),
    [run, sessionId],
  );

  const undo = useCallback(
    () =>
      run(
        (signal) => undoStudio(sessionId, {
          expectedVersion: snapshotRef.current?.active_version_id,
          signal,
        }),
        () => ({ kind: "info", text: "Undone." }),
      ),
    [run, sessionId],
  );

  const redo = useCallback(
    () =>
      run(
        (signal) => redoStudio(sessionId, {
          expectedVersion: snapshotRef.current?.active_version_id,
          signal,
        }),
        () => ({ kind: "info", text: "Redone." }),
      ),
    [run, sessionId],
  );

  const branch = useCallback(
    (name?: string, fromVersionId?: string) =>
      run(
        (signal) =>
          createStudioBranch(
            sessionId,
            { name, from_version_id: fromVersionId },
            { expectedVersion: snapshotRef.current?.active_version_id, signal },
          ),
        (next) => ({ kind: "success", text: `Branch “${next.active_branch_name}” created.` }),
      ),
    [run, sessionId],
  );

  const switchBranch = useCallback(
    (branchId: string) =>
      run((signal) =>
        switchStudioBranch(sessionId, branchId, {
          expectedVersion: snapshotRef.current?.active_version_id,
          signal,
        }),
      ),
    [run, sessionId],
  );

  const saveWorld = useCallback(
    async (name: string, description: string): Promise<StudioWorldSaveResult | null> => {
      mutationAbortRef.current?.abort();
      const controller = new AbortController();
      mutationAbortRef.current = controller;
      const seq = ++mutationSeqRef.current;
      busyRef.current = true;
      setBusy(true);
      setNotice(null);
      try {
        const world = await saveStudioWorld(
          sessionId,
          { name, description },
          { signal: controller.signal },
        );
        if (controller.signal.aborted || seq !== mutationSeqRef.current) return null;
        setNotice({ kind: "success", text: `Saved “${world.name}” to your worlds.` });
        return world;
      } catch (error) {
        if (controller.signal.aborted || seq !== mutationSeqRef.current) return null;
        setNotice({ kind: "error", text: messageOf(error) });
        return null;
      } finally {
        if (seq === mutationSeqRef.current) {
          mutationAbortRef.current = null;
          busyRef.current = false;
          setBusy(false);
        }
      }
    },
    [sessionId],
  );

  return {
    snapshot,
    loading,
    busy,
    connected,
    notice,
    loadError,
    setNotice,
    clearNotice: () => setNotice(null),
    reload: load,
    refine,
    regenerate,
    selectCandidate,
    commands,
    undo,
    redo,
    branch,
    switchBranch,
    saveWorld,
  };
}
