"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export type AnimusCommandGroup = "Create" | "Session" | "View" | "Edit" | "Export" | "Help" | "Explore";

export interface AnimusCommand {
  id: string;
  label: string;
  detail: string;
  group: AnimusCommandGroup;
  keywords?: string;
  disabled?: boolean;
  disabledReason?: string;
  run: () => void;
}

interface CommandRegistryValue {
  commands: AnimusCommand[];
  setCommands: (commands: AnimusCommand[]) => void;
}

const CommandRegistryContext = createContext<CommandRegistryValue | null>(null);

export function AnimusCommandProvider({ children }: { children: ReactNode }) {
  const [commands, setCommandsState] = useState<AnimusCommand[]>([]);
  const setCommands = useCallback((next: AnimusCommand[]) => setCommandsState(next), []);
  const value = useMemo(() => ({ commands, setCommands }), [commands, setCommands]);
  return <CommandRegistryContext.Provider value={value}>{children}</CommandRegistryContext.Provider>;
}

export function useAnimusCommands(): CommandRegistryValue {
  const value = useContext(CommandRegistryContext);
  if (!value) throw new Error("useAnimusCommands must be used inside AnimusCommandProvider");
  return value;
}

export function useOptionalAnimusCommands(): CommandRegistryValue | null {
  return useContext(CommandRegistryContext);
}
