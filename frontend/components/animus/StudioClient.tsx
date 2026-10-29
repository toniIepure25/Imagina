"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import dynamic from "next/dynamic";
import AnimusShell from "@/components/animus/AnimusShell";
import Button from "@/components/common/Button";
import ButtonLink from "@/components/common/ButtonLink";
import CandidateStrip from "@/components/animus/CandidateStrip";
import FirstLookGate from "@/components/animus/FirstLookGate";
import InspectorPanel from "@/components/animus/InspectorPanel";
import PromptBar from "@/components/animus/PromptBar";
import LedgerView from "@/components/animus/workbench/LedgerView";
import PreviewBanner, { PreviewPanel } from "@/components/animus/workbench/PreviewBanner";
import SaveWorldDialog from "@/components/animus/workbench/SaveWorldDialog";
import StructureView from "@/components/animus/workbench/StructureView";
import TraceView from "@/components/animus/workbench/TraceView";
import VersionTimecode from "@/components/animus/workbench/VersionTimecode";
import { compareScenes } from "@/lib/sceneCompare";
import { buildWorkbenchQuery, parseWorkbenchQuery } from "@/lib/workbenchUrl";
import WorkbenchToolbar from "@/components/animus/workbench/WorkbenchToolbar";
import { WorkbenchProvider, useWorkbench } from "@/components/animus/workbench/WorkbenchProvider";
import { useAnimusCommands, type AnimusCommand } from "@/components/animus/AnimusCommandRegistry";
import {
  getStudioVersion,
  type SceneCommand,
  type SceneRelation,
  type StudioApiError,
  type StudioSnapshot,
  type StudioVersionDetail,
} from "@/lib/animusStudioApi";
import { useAnimusStudio } from "@/lib/useAnimusStudio";
import { relationLabel, type SceneRelationName } from "@/lib/sceneContract";
import { AnimusCommandProvider } from "@/components/animus/AnimusCommandRegistry";
import { type StageLayer, type WorkbenchPreview, type WorkbenchView } from "@/lib/workbenchState";

const AnimusScene = dynamic(() => import("@/components/animus/AnimusScene"), {
  ssr: false,
  loading: () => (
    <div
      className="flex min-h-[48vh] flex-1 items-center justify-center bg-[#050711] xl:min-h-0"
      role="status"
      aria-live="polite"
    >
      <div className="text-center">
        <div className="mx-auto h-10 w-10 animate-pulse rounded-full border border-dashed border-signal/40" />
        <p className="mt-3 font-mono text-[11px] uppercase tracking-[0.16em] text-foreground/40">
          Loading spatial stage
        </p>
      </div>
    </div>
  ),
});

const CompareChamber = dynamic(() => import("@/components/animus/workbench/CompareChamber"), {
  ssr: false,
});

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

type StudioController = ReturnType<typeof useAnimusStudio>;

function StudioWorkspace({ studio, sessionId }: { studio: StudioController; sessionId: string }) {
  const snapshot = studio.snapshot!;
  const {
    busy,
    connected,
    notice,
    selectCandidate,
    commands,
    undo,
    redo,
    branch,
    switchBranch,
    saveWorld: saveWorldToLibrary,
    regenerate,
    refine,
    setNotice,
  } = studio;
  const { state, dispatch } = useWorkbench();
  const { setCommands } = useAnimusCommands();
  const [cameraPreset, setCameraPreset] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [blinkOn, setBlinkOn] = useState(false);
  const [blinkPhase, setBlinkPhase] = useState<"head" | "preview">("head");
  const blinkTimerRef = useRef<number | null>(null);
  const [saveOpen, setSaveOpen] = useState(false);
  const [comparePreview, setComparePreview] = useState<WorkbenchPreview>(null);
  const [savingWorld, setSavingWorld] = useState(false);
  const [firstLookDismissed, setFirstLookDismissed] = useState<boolean>(() => {
    try {
      return window.sessionStorage.getItem(`animus.firstLook.${sessionId}`) === "1";
    } catch {
      return false;
    }
  });
  const cacheRef = useRef<Map<string, StudioVersionDetail>>(new Map());
  const abortRef = useRef<AbortController | null>(null);
  const linkAppliedRef = useRef(false);
  const urlHydratedRef = useRef(false);
  const firstLookKey = `animus.firstLook.${sessionId}`;

  const preview = state.preview;
  const displayScene = preview
    ? preview.kind === "candidate"
      ? preview.candidate.scene
      : preview.version.scene
    : snapshot?.scene;
  const spatialDiff = useMemo(
    () => (preview && displayScene && snapshot ? compareScenes(snapshot.scene, displayScene) : null),
    [displayScene, preview, snapshot],
  );
  const panelDiff = preview?.kind === "candidate" ? preview.candidate.diff : spatialDiff;
  const diffBasis = preview?.kind === "candidate" ? "Since source version" : "Since head";
  const focusableIds = useMemo(
    () => new Set(displayScene?.entities.map((entity) => entity.id) ?? []),
    [displayScene],
  );
  const readOnly = preview !== null;
  const blinkScene = blinkOn ? (blinkPhase === "preview" ? displayScene : snapshot.scene) : null;
  const blinkCameraView = blinkOn
    ? {
        position: snapshot.scene.camera.position,
        target: snapshot.scene.camera.target,
        fov: snapshot.scene.camera.fov,
      }
    : null;
  const selectedEntity = displayScene?.entities.find((entity) => entity.id === state.selectedId) ?? null;
  const canTransformSelection = Boolean(selectedEntity && !selectedEntity.locked && !readOnly);
  const previewStale =
    preview?.kind === "candidate" && preview.candidate.source_version_id !== snapshot?.active_version_id;
  const previewCandidateId = preview?.kind === "candidate" ? preview.candidate.candidate_id : null;
  const compareOpen = Boolean(comparePreview && comparePreview === preview && spatialDiff && !previewStale);
  const compareBasis = preview?.kind === "candidate" ? "Head vs candidate" : "Since head";
  const headLabel = `v${snapshot.version.number} · ${snapshot.active_branch_name}`;
  const previewLabel =
    preview?.kind === "version"
      ? `v${preview.version.number}`
      : preview?.kind === "candidate"
        ? `Candidate ${String.fromCharCode(65 + preview.candidate.variant_index)}`
        : "";
  const firstLookDone = firstLookDismissed || snapshot.history.length > 1;
  const firstLookOpen = !firstLookDone;

  useEffect(() => {
    if (!displayScene) return;
    dispatch({ type: "prune_selection", entityIds: displayScene.entities.map((entity) => entity.id) });
  }, [dispatch, displayScene]);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  const reveal = useCallback(() => {
    setFirstLookDismissed(true);
    try {
      window.sessionStorage.setItem(firstLookKey, "1");
    } catch {
      // Session storage may be disabled; the gate still closes for this mount.
    }
  }, [firstLookKey]);

  const stopBlink = useCallback(() => {
    if (blinkTimerRef.current !== null) {
      window.clearInterval(blinkTimerRef.current);
      blinkTimerRef.current = null;
    }
    setBlinkOn(false);
    setBlinkPhase("head");
  }, []);

  const previewCandidate = useCallback(
    (candidate: StudioSnapshot["candidates"][number]) => {
      setPreviewError(null);
      if (preview?.kind === "candidate" && preview.candidate.candidate_id === candidate.candidate_id) {
        stopBlink();
        dispatch({ type: "clear_preview" });
        return;
      }
      dispatch({ type: "preview", preview: { kind: "candidate", candidate } });
    },
    [dispatch, preview, stopBlink],
  );

  const previewVersion = useCallback(
    async (versionId: string): Promise<boolean> => {
      if (!snapshot) return false;
      if (preview?.kind === "version" && preview.version.version_id === versionId) {
        stopBlink();
        dispatch({ type: "clear_preview" });
        return true;
      }
      if (versionId === snapshot.active_version_id) {
        stopBlink();
        dispatch({ type: "clear_preview" });
        return true;
      }
      setPreviewError(null);
      const cached = cacheRef.current.get(versionId);
      if (cached) {
        dispatch({ type: "preview", preview: { kind: "version", version: cached } });
        return true;
      }
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      setPreviewLoading(true);
      try {
        const detail = await getStudioVersion(sessionId, versionId, { signal: controller.signal });
        cacheRef.current.set(versionId, detail);
        if (cacheRef.current.size > 20) {
          const oldest = cacheRef.current.keys().next().value;
          if (oldest) cacheRef.current.delete(oldest);
        }
        dispatch({ type: "preview", preview: { kind: "version", version: detail } });
        return true;
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") return false;
        setPreviewError(error instanceof Error ? error.message : "The version could not be loaded.");
        return false;
      } finally {
        if (abortRef.current === controller) {
          setPreviewLoading(false);
          abortRef.current = null;
        }
      }
    },
    [dispatch, preview, sessionId, snapshot, stopBlink],
  );

  const orderedVersions = useMemo(
    () => (snapshot ? snapshot.history.slice().sort((a, b) => a.number - b.number) : []),
    [snapshot],
  );
  const activeVersionId = snapshot?.active_version_id;
  const currentVersionIndex = useMemo(() => {
    const currentId = preview?.kind === "version" ? preview.version.version_id : activeVersionId;
    return orderedVersions.findIndex((version) => version.version_id === currentId);
  }, [activeVersionId, orderedVersions, preview]);

  const stepVersion = useCallback(
    async (delta: number) => {
      const next = orderedVersions[currentVersionIndex + delta];
      if (next) await previewVersion(next.version_id);
    },
    [currentVersionIndex, orderedVersions, previewVersion],
  );

  const toggleBlink = useCallback(() => {
    if (blinkOn) {
      stopBlink();
      return;
    }
    if (!preview || !displayScene) return;
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) {
      setNotice({
        kind: "info",
        text: "Blink comparison is unavailable when reduced motion is on. Compare side by side instead.",
      });
      return;
    }
    setBlinkOn(true);
    setBlinkPhase("preview");
    let ticks = 0;
    blinkTimerRef.current = window.setInterval(() => {
      ticks += 1;
      if (ticks >= 6) {
        stopBlink();
        return;
      }
      setBlinkPhase((phase) => (phase === "head" ? "preview" : "head"));
    }, 1100);
  }, [blinkOn, displayScene, preview, setNotice, stopBlink]);

  useEffect(() => {
    return () => {
      if (blinkTimerRef.current !== null) window.clearInterval(blinkTimerRef.current);
    };
  }, []);

  const discardPreview = useCallback(() => {
    stopBlink();
    dispatch({ type: "clear_preview" });
    setPreviewError(null);
  }, [dispatch, stopBlink]);

  const openCompare = useCallback(() => {
    if (!preview || previewStale) return;
    setComparePreview(preview);
  }, [preview, previewStale]);

  const closeCompare = useCallback(() => setComparePreview(null), []);

  const focusEntity = useCallback(
    (entityId: string) => {
      if (!displayScene?.entities.some((entity) => entity.id === entityId)) return;
      dispatch({ type: "select", entityId });
      setCameraPreset("detail");
    },
    [displayScene, dispatch],
  );

  const keepPreview = useCallback(async () => {
    if (!preview) return;
    if (preview.kind === "candidate") {
      if (previewStale) return;
      const result = await selectCandidate(preview.candidate);
      if (result) {
        stopBlink();
        dispatch({ type: "clear_preview" });
      }
      return;
    }
    const result = await branch(undefined, preview.version.version_id);
    if (result) {
      stopBlink();
      dispatch({ type: "clear_preview" });
    }
  }, [branch, dispatch, preview, previewStale, selectCandidate, stopBlink]);

  const branchPreview = useCallback(async () => {
    if (preview?.kind !== "version") return;
    const result = await branch(undefined, preview.version.version_id);
    if (result) {
      stopBlink();
      dispatch({ type: "clear_preview" });
    }
  }, [branch, dispatch, preview, stopBlink]);

  const applyTransform = useCallback(
    async (next: {
      entityId: string;
      position: [number, number, number];
      rotation: [number, number, number];
      scale: [number, number, number];
    }) => {
      if (readOnly) return false;
      setPreviewError(null);
      const payload: SceneCommand[] = [
        {
          op: "set_entity_transform",
          entity_id: next.entityId,
          position: next.position,
          rotation: next.rotation,
          scale: next.scale,
        },
      ];
      const result = await commands(payload, "direct manipulation");
      if (!result) setPreviewError("The transform was not accepted. The scene was restored.");
      return Boolean(result);
    },
    [commands, readOnly],
  );

  const moveInStructure = useCallback(
    async (entityId: string, x: number, z: number) => {
      if (readOnly) return false;
      const entity = snapshot.scene.entities.find((item) => item.id === entityId);
      if (!entity) return false;
      const result = await commands(
        [
          {
            op: "set_entity_transform",
            entity_id: entityId,
            position: [x, entity.transform.position[1], z],
            rotation: entity.transform.rotation,
            scale: entity.transform.scale,
          },
        ],
        "structure move",
      );
      if (!result) setPreviewError("The move was not accepted. The scene is unchanged.");
      return Boolean(result);
    },
    [commands, readOnly, snapshot],
  );

  const addRelation = useCallback(
    async (subjectId: string, relation: SceneRelationName, objectId: string) => {
      if (readOnly) return false;
      const result = await commands(
        [{ op: "set_relation", subject_id: subjectId, relation, object_id: objectId }],
        `relation: ${relationLabel(relation)}`,
      );
      return Boolean(result);
    },
    [commands, readOnly],
  );

  const removeRelation = useCallback(
    async (relation: SceneRelation) => {
      if (readOnly) return false;
      const result = await commands(
        [
          {
            op: "remove_relation",
            subject_id: relation.subject_id,
            relation: relation.relation,
            object_id: relation.object_id,
          },
        ],
        "remove relation",
      );
      return Boolean(result);
    },
    [commands, readOnly],
  );

  const lockSelected = useCallback(async () => {
    if (!selectedEntity || readOnly) return;
    await commands(
      [{ op: "lock", entity_id: selectedEntity.id, locked: !selectedEntity.locked }],
      selectedEntity.locked ? "unlock element" : "lock element",
    );
  }, [commands, readOnly, selectedEntity]);

  const setView = useCallback(
    (view: WorkbenchView) => {
      dispatch({ type: "view", view });
    },
    [dispatch],
  );

  useEffect(() => {
    if (linkAppliedRef.current) return;
    linkAppliedRef.current = true;
    const link = parseWorkbenchQuery(window.location.search);
    if (!link.view && !link.versionId && !link.candidateId) return;
    if (link.view) setView(link.view);
    const apply = async () => {
      if (link.versionId) {
        const applied = await previewVersion(link.versionId);
        if (!applied) {
          setPreviewError("The linked preview is not available in this branch.");
          window.history.replaceState(null, "", window.location.pathname);
        }
        return;
      }
      if (link.candidateId) {
        const candidate = snapshot.candidates.find((item) => item.candidate_id === link.candidateId);
        if (candidate) previewCandidate(candidate);
        else {
          setPreviewError("The linked candidate is no longer available.");
          window.history.replaceState(null, "", window.location.pathname);
        }
      }
    };
    void apply();
  }, [previewCandidate, previewVersion, setView, snapshot.candidates]);

  useEffect(() => {
    if (!urlHydratedRef.current) {
      urlHydratedRef.current = true;
      return;
    }
    const query = buildWorkbenchQuery({
      view: state.view,
      versionId: preview?.kind === "version" ? preview.version.version_id : null,
      candidateId: preview?.kind === "candidate" ? preview.candidate.candidate_id : null,
    });
    const next = `${window.location.pathname}${query}${window.location.hash}`;
    const current = `${window.location.pathname}${window.location.search}${window.location.hash}`;
    if (next !== current) window.history.replaceState(window.history.state, "", next);
  }, [preview, state.view]);

  const toggleLayer = useCallback(
    (layer: StageLayer) => {
      dispatch({ type: "layer", layer });
    },
    [dispatch],
  );

  const exportScene = useCallback(() => {
    if (!snapshot) return;
    const blob = new Blob([JSON.stringify(snapshot.scene, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `animus-${sessionId}-v${snapshot.version.number}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }, [sessionId, snapshot]);

  useEffect(() => {
    if (!snapshot) return;
    const commands: AnimusCommand[] = [
      {
        id: "workbench-stage",
        label: "Show Stage",
        detail: "Spatial view with direct manipulation",
        group: "View",
        keywords: "3d scene",
        run: () => setView("stage"),
      },
      {
        id: "workbench-structure",
        label: "Show Structure",
        detail: "Graph and relation editor",
        group: "View",
        keywords: "graph nodes relations",
        run: () => setView("structure"),
      },
      {
        id: "workbench-ledger",
        label: "Show Ledger",
        detail: "Version and branch graph",
        group: "View",
        keywords: "history versions branches",
        run: () => setView("ledger"),
      },
      {
        id: "workbench-trace",
        label: "Show Trace",
        detail: "Event-by-event account of intents, commands, and candidates",
        group: "View",
        keywords: "trace events log intent commands diff",
        run: () => setView("trace"),
      },
      {
        id: "workbench-focus",
        label: state.focusMode ? "Leave focus mode" : "Enter focus mode",
        detail: "Hide the candidate strip and non-essential chrome",
        group: "View",
        keywords: "focus quiet",
        run: () => dispatch({ type: "focus", enabled: !state.focusMode }),
      },
      {
        id: "version-previous",
        label: "Preview previous version",
        detail: currentVersionIndex > 0 ? `Step back to v${orderedVersions[currentVersionIndex - 1].number}` : "Already at the first version",
        group: "View",
        keywords: "timecode history older back",
        disabled: currentVersionIndex <= 0,
        disabledReason: "Already at the first version",
        run: () => void stepVersion(-1),
      },
      {
        id: "version-next",
        label: "Preview next version",
        detail:
          currentVersionIndex >= 0 && currentVersionIndex < orderedVersions.length - 1
            ? `Step forward to v${orderedVersions[currentVersionIndex + 1].number}`
            : "Already at the newest version",
        group: "View",
        keywords: "timecode history newer forward",
        disabled: currentVersionIndex < 0 || currentVersionIndex >= orderedVersions.length - 1,
        disabledReason: "Already at the newest version",
        run: () => void stepVersion(1),
      },
      {
        id: "workbench-lock",
        label: selectedEntity?.locked ? "Unlock selected element" : "Lock selected element",
        detail: selectedEntity ? selectedEntity.label : "Select an element first",
        group: "Edit",
        keywords: "lock preserve",
        disabled: !selectedEntity || readOnly,
        disabledReason: readOnly ? "Preview is read-only" : "Select an element first",
        run: () => void lockSelected(),
      },
      {
        id: "workbench-undo",
        label: "Undo",
        detail: snapshot.has_undo ? "Restore the previous version" : "Nothing to undo",
        group: "Edit",
        keywords: "back revert",
        disabled: !snapshot.has_undo,
        disabledReason: "Nothing to undo",
        run: () => void undo(),
      },
      {
        id: "workbench-redo",
        label: "Redo",
        detail: snapshot.has_redo ? "Reapply the next version" : "Nothing to redo",
        group: "Edit",
        keywords: "forward",
        disabled: !snapshot.has_redo,
        disabledReason: "Nothing to redo",
        run: () => void redo(),
      },
      ...(preview
        ? [
            {
              id: "workbench-blink",
              label: blinkOn ? "Stop blink comparison" : "Blink head and preview",
              detail: "Manually alternate both scenes in the same camera",
              group: "View" as const,
              keywords: "blink flicker compare toggle temporal",
              disabled: previewLoading || Boolean(previewStale),
              disabledReason: previewLoading ? "Still loading" : "Preview is stale",
              run: toggleBlink,
            },
            {
              id: "workbench-compare",
              label: "Compare with head",
              detail: "Open the side-by-side comparison chamber",
              group: "View" as const,
              keywords: "chamber split side by side compare",
              disabled: previewLoading || Boolean(previewStale),
              disabledReason: previewLoading ? "Still loading" : "Preview is stale",
              run: openCompare,
            },
            {
              id: "workbench-keep",
              label: "Keep the preview",
              detail: preview.kind === "candidate" ? "Create a version from this candidate" : "Branch from this version",
              group: "Edit" as const,
              keywords: "commit keep preview branch",
              disabled: previewLoading || Boolean(previewStale),
              disabledReason: previewLoading ? "Still loading" : "Preview is stale",
              run: () => void keepPreview(),
            },
            {
              id: "workbench-return",
              label: "Return to head",
              detail: "Discard the preview without writing",
              group: "View" as const,
              keywords: "cancel preview",
              run: discardPreview,
            },
          ]
        : []),
      {
        id: "workbench-export",
        label: "Export scene JSON",
        detail: "Download the current symbolic scene graph",
        group: "Export",
        keywords: "download json",
        run: exportScene,
      },
    ];
    setCommands(commands);
    return () => setCommands([]);
  }, [
    blinkOn,
    discardPreview,
    dispatch,
    exportScene,
    keepPreview,
    lockSelected,
    currentVersionIndex,
    openCompare,
    orderedVersions,
    preview,
    previewLoading,
    previewStale,
    readOnly,
    redo,
    selectedEntity,
    setCommands,
    setView,
    snapshot,
    state.focusMode,
    stepVersion,
    toggleBlink,
    undo,
  ]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (event.key === "Escape" && compareOpen) {
        event.preventDefault();
        closeCompare();
        return;
      }
      if (target?.closest("input, textarea, select, [contenteditable='true']")) return;
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "z" && snapshot) {
        event.preventDefault();
        if (event.shiftKey) void redo();
        else void undo();
        return;
      }
      if (event.metaKey || event.ctrlKey || event.altKey) return;
      if (event.key === "Escape") {
        if (compareOpen) {
          closeCompare();
          return;
        }
        if (preview) discardPreview();
        else dispatch({ type: "select", entityId: null });
        return;
      }
      if (event.key === "1") setView("stage");
      else if (event.key === "2") setView("structure");
      else if (event.key === "3") setView("ledger");
      else if (event.key === "4") setView("trace");
      else if (event.key === "[") {
        event.preventDefault();
        void stepVersion(-1);
      } else if (event.key === "]") {
        event.preventDefault();
        void stepVersion(1);
      } else if (event.key.toLowerCase() === "c" && preview && !previewStale) {
        event.preventDefault();
        if (compareOpen) closeCompare();
        else openCompare();
      } else if (event.key.toLowerCase() === "b" && (blinkOn || (preview && !previewStale))) {
        event.preventDefault();
        toggleBlink();
      } else if (event.key.toLowerCase() === "f") dispatch({ type: "focus", enabled: !state.focusMode });
      else if (event.key.toLowerCase() === "l") void lockSelected();
      else if (event.key.toLowerCase() === "g" && canTransformSelection) dispatch({ type: "gizmo", mode: "translate" });
      else if (event.key.toLowerCase() === "r" && canTransformSelection) dispatch({ type: "gizmo", mode: "rotate" });
      else if (event.key.toLowerCase() === "s" && canTransformSelection) dispatch({ type: "gizmo", mode: "scale" });
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [
    blinkOn,
    canTransformSelection,
    closeCompare,
    compareOpen,
    discardPreview,
    dispatch,
    lockSelected,
    openCompare,
    preview,
    previewStale,
    redo,
    setView,
    snapshot,
    state.focusMode,
    stepVersion,
    toggleBlink,
    undo,
  ]);

  const saveWorld = useCallback(
    async (name: string, description: string) => {
      setSavingWorld(true);
      const result = await saveWorldToLibrary(name, description);
      setSavingWorld(false);
      if (result) setSaveOpen(false);
      return Boolean(result);
    },
    [saveWorldToLibrary],
  );

  if (!snapshot) return null;

  return (
    <AnimusShell sessionId={sessionId} active="studio" workspace>
      <div className="flex min-h-0 flex-1 flex-col xl:grid xl:h-full xl:grid-cols-[minmax(0,1fr)_370px] xl:overflow-hidden">
        <section className="flex min-h-0 flex-1 flex-col">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-surface-border bg-background/70 px-3 py-2">
            <div className="flex min-w-0 items-center gap-3">
              <ButtonLink href="/animus" variant="ghost" size="sm" className="shrink-0 px-0 text-[11px] text-foreground/40">
                ← Animus
              </ButtonLink>
              <div className="min-w-0">
                <h1 className="truncate font-display text-base text-foreground/90">{snapshot.title}</h1>
                <div className="flex items-center gap-2 font-mono text-[11px] text-foreground/35">
                  <span data-testid="studio-version">v{snapshot.version.number}</span>
                  <span>·</span>
                  <span data-testid="studio-branch">{snapshot.active_branch_name}</span>
                  <span>·</span>
                  <span>{snapshot.history.length} versions</span>
                  <span>·</span>
                  <span data-testid="studio-connection" className="inline-flex items-center gap-1">
                    <span
                      className={`h-1.5 w-1.5 rounded-full ${connected ? "bg-emerald-400" : "bg-foreground/25"}`}
                    />
                    {connected ? "live" : "local"}
                  </span>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="hidden rounded-full border border-signal/25 bg-signal/5 px-2 py-1 font-mono text-[11px] uppercase tracking-[0.12em] text-signal/75 sm:inline">
                L1 · behavioral-assisted
              </span>
              <Button
                size="sm"
                variant="ghost"
                disabled={busy || !snapshot.has_undo}
                onClick={() => void undo()}
                className="text-[11px]"
              >
                Undo
              </Button>
              <Button
                size="sm"
                variant="ghost"
                disabled={busy || !snapshot.has_redo}
                onClick={() => void redo()}
                className="text-[11px]"
              >
                Redo
              </Button>
              <Button
                size="sm"
                variant="secondary"
                disabled={busy || savingWorld || readOnly}
                onClick={() => setSaveOpen(true)}
                className="text-[11px]"
              >
                Save world
              </Button>
            </div>
          </div>

          <WorkbenchToolbar
            view={state.view}
            onView={setView}
            layers={state.layers}
            onToggleLayer={toggleLayer}
            gizmoMode={state.gizmoMode}
            onGizmoMode={(mode) => dispatch({ type: "gizmo", mode })}
            hasSelection={Boolean(selectedEntity)}
            selectionLocked={Boolean(selectedEntity?.locked)}
            readOnly={readOnly}
            focusMode={state.focusMode}
            onToggleFocus={() => dispatch({ type: "focus", enabled: !state.focusMode })}
            cameraPreset={cameraPreset}
            onCameraPreset={setCameraPreset}
          />

          {!firstLookOpen && state.view === "stage" && !state.focusMode ? (
            <VersionTimecode
              versions={orderedVersions}
              activeVersionId={snapshot.active_version_id}
              previewVersionId={preview?.kind === "version" ? preview.version.version_id : null}
              busy={previewLoading}
              onPreview={(versionId) => void previewVersion(versionId)}
            />
          ) : null}

          {preview ? (
            <PreviewBanner
              preview={preview}
              stale={Boolean(previewStale)}
              busy={busy || previewLoading}
              blinkOn={blinkOn}
              onBlink={toggleBlink}
              onKeep={() => void keepPreview()}
              onDiscard={discardPreview}
              onBranch={() => void branchPreview()}
              onCompare={openCompare}
            />
          ) : null}

          {previewError ? (
            <div role="alert" className="border-b border-danger/25 bg-danger/10 px-3 py-1.5 text-[11px] text-red-200/85">
              {previewError}
            </div>
          ) : null}

          {firstLookOpen ? (
            <div className="flex-1 p-3">
              <FirstLookGate scene={snapshot.scene} intention={snapshot.title} onReveal={reveal} />
            </div>
          ) : state.view === "stage" ? (
            <div id="workbench-view-stage" role="tabpanel" aria-label="Stage" className="flex min-h-0 flex-1 flex-col">
              {blinkOn ? (
                <div role="status" aria-live="polite" className="sr-only">
                  Blink comparison running. Showing {blinkPhase === "head" ? "the committed head" : "the preview"} in
                  the same camera. Press B or Stop blink to end.
                </div>
              ) : null}
              <AnimusScene
                scene={blinkScene ?? displayScene ?? snapshot.scene}
                selectedId={blinkOn ? null : state.selectedId}
                onSelect={(entityId) => {
                  if (!blinkOn) dispatch({ type: "select", entityId });
                }}
                className="min-h-[48vh] flex-1 xl:min-h-0"
                dpr={[1, 1.5]}
                frameloop={blinkOn ? "demand" : "always"}
                layers={
                  blinkOn
                    ? { ...state.layers, changes: false, relations: false, labels: false, locks: false, grid: false, provenance: false }
                    : state.layers
                }
                gizmoMode={state.gizmoMode}
                readOnly={readOnly}
                interactive={!blinkOn}
                showOverlay={!blinkOn}
                animate={!blinkOn}
                cameraPreset={blinkOn ? null : cameraPreset}
                cameraView={blinkCameraView}
                diff={blinkOn ? null : spatialDiff}
                traceScene={blinkOn ? null : preview ? snapshot.scene : null}
                onCameraInteract={() => setCameraPreset(null)}
                onTransform={blinkOn ? undefined : applyTransform}
              />
            </div>
          ) : state.view === "structure" ? (
            <div
              id="workbench-view-structure"
              role="tabpanel"
              aria-label="Structure"
              className="min-h-0 flex-1 overflow-y-auto"
            >
              <StructureView
                scene={displayScene ?? snapshot.scene}
                selectedId={state.selectedId}
                onSelect={(entityId) => dispatch({ type: "select", entityId })}
                onMove={moveInStructure}
                onAddRelation={addRelation}
                onRemoveRelation={removeRelation}
                readOnly={readOnly}
                busy={busy || previewLoading}
              />
            </div>
          ) : state.view === "ledger" ? (
            <div
              id="workbench-view-ledger"
              role="tabpanel"
              aria-label="Ledger"
              className="min-h-0 flex-1 overflow-y-auto"
            >
              <LedgerView
                snapshot={snapshot}
                previewVersionId={preview?.kind === "version" ? preview.version.version_id : null}
                onPreview={(versionId) => void previewVersion(versionId)}
                onBranch={(versionId) => void branch(undefined, versionId)}
                onTrace={() => setView("trace")}
                busy={busy || previewLoading}
              />
            </div>
          ) : (
            <div
              id="workbench-view-trace"
              role="tabpanel"
              aria-label="Trace"
              className="min-h-0 flex-1 overflow-y-auto"
            >
              <TraceView
                snapshot={snapshot}
                previewVersionId={preview?.kind === "version" ? preview.version.version_id : null}
                busy={busy || previewLoading}
                onPreview={(versionId) => void previewVersion(versionId)}
              />
            </div>
          )}

          {!firstLookOpen && state.view === "stage" && !state.focusMode && (!readOnly || preview?.kind === "candidate") ? (
            <CandidateStrip
              candidates={snapshot.candidates}
              activeHash={snapshot.scene.metadata.content_hash ?? ""}
              currentVersionId={snapshot.active_version_id}
              previewCandidateId={previewCandidateId}
              busy={busy}
              onPreview={previewCandidate}
              onSelect={selectCandidate}
              onRegenerate={() => regenerate([])}
            />
          ) : null}
          {!firstLookOpen && state.view === "stage" && !state.focusMode && !readOnly ? (
            <PromptBar
              busy={busy}
              notice={notice}
              onSubmit={refine}
              onClearNotice={() => setNotice(null)}
              onOpenTrace={() => setView("trace")}
            />
          ) : null}
        </section>

        <aside className="min-h-0 border-t border-surface-border bg-[#080a0c]/70 xl:border-l xl:border-t-0">
          {preview ? (
            <PreviewPanel
              preview={preview}
              diff={panelDiff}
              diffBasis={diffBasis}
              stale={Boolean(previewStale)}
              busy={busy || previewLoading}
              blinkOn={blinkOn}
              focusableIds={focusableIds}
              onFocusEntity={focusEntity}
              onBlink={toggleBlink}
              onKeep={() => void keepPreview()}
              onDiscard={discardPreview}
              onBranch={() => void branchPreview()}
              onCompare={openCompare}
            />
          ) : (
            <InspectorPanel
              snapshot={snapshot}
              selectedId={state.selectedId}
              busy={busy}
              onSelect={(entityId) => dispatch({ type: "select", entityId })}
              onCommands={commands}
              onUndo={undo}
              onRedo={redo}
              onBranch={branch}
              onSwitchBranch={switchBranch}
              onSaveWorld={saveWorldToLibrary}
            />
          )}
        </aside>
      </div>
      {compareOpen && spatialDiff && displayScene ? (
        <CompareChamber
          head={snapshot.scene}
          preview={displayScene}
          diff={spatialDiff}
          headLabel={headLabel}
          previewLabel={previewLabel}
          basis={compareBasis}
          candidate={preview?.kind === "candidate"}
          onClose={closeCompare}
        />
      ) : null}
      {saveOpen ? (
        <SaveWorldDialog
          open
          defaultName={`${snapshot.title} world`}
          busy={savingWorld}
          onClose={() => setSaveOpen(false)}
          onSave={saveWorld}
        />
      ) : null}
    </AnimusShell>
  );
}

export default function StudioClient({ sessionId }: { sessionId: string }) {
  const studio = useAnimusStudio(sessionId);
  const failure = loadErrorCopy(studio.loadError);

  if (studio.loading && !studio.snapshot) {
    return (
      <AnimusShell sessionId={sessionId} active="studio" workspace>
        <div className="flex min-h-[50vh] flex-1 items-center justify-center" aria-busy="true">
          <div className="space-y-3 text-center">
            <div className="mx-auto h-9 w-9 animate-spin rounded-full border-2 border-signal/20 border-t-signal" />
            <p className="text-xs text-foreground/40" role="status">Opening your studio…</p>
          </div>
        </div>
      </AnimusShell>
    );
  }

  if (!studio.snapshot) {
    return (
      <AnimusShell sessionId={sessionId} active="studio" workspace>
        <div className="flex min-h-[60vh] flex-1 items-center justify-center p-6">
          <div className="glass max-w-md space-y-4 p-6 text-center" role="alert">
            <h1 className="text-lg font-semibold">{failure.title}</h1>
            <p className="text-xs leading-relaxed text-foreground/50">{failure.body}</p>
            <div className="flex justify-center gap-2">
              <Button size="sm" variant="secondary" onClick={() => void studio.reload()}>
                Try again
              </Button>
              <ButtonLink href="/animus" size="sm">
                Back to Animus
              </ButtonLink>
            </div>
          </div>
        </div>
      </AnimusShell>
    );
  }

  return (
    <AnimusCommandProvider>
      <WorkbenchProvider>
        <StudioWorkspace studio={studio} sessionId={sessionId} />
      </WorkbenchProvider>
    </AnimusCommandProvider>
  );
}
