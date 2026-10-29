"use client";

import { usePathname } from "next/navigation";
import { useCallback, useMemo, useState, useSyncExternalStore, type ReactNode } from "react";
import { getEvidence } from "@/lib/evidence/registry";
import {
  defaultEvidenceSurface,
  getGlassBoxPreference,
  getServerGlassBoxPreference,
  setGlassBoxPreference,
  subscribeGlassBox,
} from "@/lib/evidence/glassboxStore";
import { GlassBoxContext, type GlassBoxContextValue } from "./GlassBoxContext";
import EvidenceDrawer from "./EvidenceDrawer";

export default function GlassBoxProvider({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const preference = useSyncExternalStore(
    subscribeGlassBox,
    getGlassBoxPreference,
    getServerGlassBoxPreference,
  );
  const [activeId, setActiveId] = useState<string | null>(null);
  const enabled = preference === "on" || (preference === "auto" && defaultEvidenceSurface(pathname));

  const openEvidence = useCallback((id: string) => {
    if (!getEvidence(id)) return;
    setActiveId(id);
  }, []);

  const closeEvidence = useCallback(() => setActiveId(null), []);

  const value = useMemo<GlassBoxContextValue>(
    () => ({
      enabled,
      preference,
      activeEntry: getEvidence(activeId),
      setPreference: setGlassBoxPreference,
      openEvidence,
      closeEvidence,
    }),
    [activeId, closeEvidence, enabled, openEvidence, preference],
  );

  return (
    <GlassBoxContext.Provider value={value}>
      {children}
      <EvidenceDrawer />
    </GlassBoxContext.Provider>
  );
}
