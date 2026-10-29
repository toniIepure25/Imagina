"use client";

import { createContext, useContext } from "react";
import type { EvidenceEntry, GlassBoxPreference } from "@/lib/evidence/types";

export type GlassBoxContextValue = {
  enabled: boolean;
  preference: GlassBoxPreference;
  activeEntry: EvidenceEntry | null;
  setPreference: (preference: GlassBoxPreference) => void;
  openEvidence: (id: string, trigger?: HTMLElement | null) => void;
  closeEvidence: () => void;
};

export const GlassBoxContext = createContext<GlassBoxContextValue | null>(null);

export function useGlassBox(): GlassBoxContextValue {
  const context = useContext(GlassBoxContext);
  if (!context) {
    throw new Error("useGlassBox must be used inside GlassBoxProvider");
  }
  return context;
}
