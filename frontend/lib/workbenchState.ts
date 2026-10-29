import type { StudioCandidate, StudioVersionDetail } from "@/lib/animusStudioApi";

export type WorkbenchView = "stage" | "structure" | "ledger" | "trace";
export type GizmoMode = "translate" | "rotate" | "scale";
export type StageLayer = "relations" | "labels" | "locks" | "provenance" | "grid" | "changes";

export type WorkbenchPreview =
  | { kind: "candidate"; candidate: StudioCandidate }
  | { kind: "version"; version: StudioVersionDetail }
  | null;

export interface WorkbenchState {
  view: WorkbenchView;
  selectedId: string | null;
  gizmoMode: GizmoMode;
  focusMode: boolean;
  preview: WorkbenchPreview;
  layers: Record<StageLayer, boolean>;
}

export const DEFAULT_LAYERS: Record<StageLayer, boolean> = {
  relations: true,
  labels: true,
  locks: true,
  provenance: false,
  grid: false,
  changes: true,
};

export const INITIAL_WORKBENCH_STATE: WorkbenchState = {
  view: "stage",
  selectedId: null,
  gizmoMode: "translate",
  focusMode: false,
  preview: null,
  layers: DEFAULT_LAYERS,
};

export type WorkbenchAction =
  | { type: "view"; view: WorkbenchView }
  | { type: "select"; entityId: string | null }
  | { type: "gizmo"; mode: GizmoMode }
  | { type: "layer"; layer: StageLayer }
  | { type: "focus"; enabled: boolean }
  | { type: "preview"; preview: Exclude<WorkbenchPreview, null> }
  | { type: "clear_preview" }
  | { type: "prune_selection"; entityIds: string[] }
  | { type: "reset" };

export function workbenchReducer(state: WorkbenchState, action: WorkbenchAction): WorkbenchState {
  switch (action.type) {
    case "view":
      return { ...state, view: action.view };
    case "select":
      return { ...state, selectedId: action.entityId };
    case "gizmo":
      return { ...state, gizmoMode: action.mode };
    case "layer":
      return {
        ...state,
        layers: { ...state.layers, [action.layer]: !state.layers[action.layer] },
      };
    case "focus":
      return { ...state, focusMode: action.enabled };
    case "preview":
      return { ...state, preview: action.preview, focusMode: false };
    case "clear_preview":
      return { ...state, preview: null };
    case "prune_selection":
      return state.selectedId && !action.entityIds.includes(state.selectedId)
        ? { ...state, selectedId: null }
        : state;
    case "reset":
      return INITIAL_WORKBENCH_STATE;
    default:
      return state;
  }
}
