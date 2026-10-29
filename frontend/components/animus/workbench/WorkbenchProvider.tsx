"use client";

import {
  createContext,
  useContext,
  useMemo,
  useReducer,
  type Dispatch,
  type ReactNode,
} from "react";
import {
  INITIAL_WORKBENCH_STATE,
  workbenchReducer,
  type WorkbenchAction,
  type WorkbenchState,
} from "@/lib/workbenchState";

interface WorkbenchContextValue {
  state: WorkbenchState;
  dispatch: Dispatch<WorkbenchAction>;
}

const WorkbenchContext = createContext<WorkbenchContextValue | null>(null);

export function WorkbenchProvider({
  children,
  state: controlledState,
  dispatch: controlledDispatch,
}: {
  children: ReactNode;
  state?: WorkbenchState;
  dispatch?: Dispatch<WorkbenchAction>;
}) {
  const [localState, localDispatch] = useReducer(workbenchReducer, INITIAL_WORKBENCH_STATE);
  const state = controlledState ?? localState;
  const dispatch = controlledDispatch ?? localDispatch;
  const value = useMemo(() => ({ state, dispatch }), [dispatch, state]);
  return <WorkbenchContext.Provider value={value}>{children}</WorkbenchContext.Provider>;
}

export function useWorkbench(): WorkbenchContextValue {
  const value = useContext(WorkbenchContext);
  if (!value) throw new Error("useWorkbench must be used inside WorkbenchProvider");
  return value;
}
