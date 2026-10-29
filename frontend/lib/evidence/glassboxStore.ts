"use client";

import type { GlassBoxPreference } from "./types";

const STORAGE_KEY = "imagina.glassbox";
let preference: GlassBoxPreference = "auto";
let hydrated = false;
let listening = false;
const listeners = new Set<() => void>();

function isPreference(value: string | null): value is GlassBoxPreference {
  return value === "auto" || value === "on" || value === "off";
}

function emit() {
  for (const listener of listeners) listener();
}

function hydrate() {
  if (hydrated || typeof window === "undefined") return;
  hydrated = true;
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (isPreference(stored)) preference = stored;
  } catch {
    preference = "auto";
  }
}

export function getGlassBoxPreference(): GlassBoxPreference {
  hydrate();
  return preference;
}

export function getServerGlassBoxPreference(): GlassBoxPreference {
  return "auto";
}

export function setGlassBoxPreference(next: GlassBoxPreference) {
  preference = next;
  hydrated = true;
  try {
    window.localStorage.setItem(STORAGE_KEY, next);
  } catch {
    // Local storage can be unavailable in private or hardened contexts.
  }
  emit();
}

export function subscribeGlassBox(listener: () => void): () => void {
  listeners.add(listener);
  if (!listening && typeof window !== "undefined") {
    listening = true;
    window.addEventListener("storage", (event) => {
      if (event.key !== STORAGE_KEY) return;
      if (isPreference(event.newValue)) {
        preference = event.newValue;
        emit();
      }
    });
  }
  return () => {
    listeners.delete(listener);
  };
}

export function defaultEvidenceSurface(pathname: string | null): boolean {
  if (!pathname) return false;
  if (pathname.startsWith("/research/participant")) return false;
  if (pathname.startsWith("/session")) return false;
  if (pathname.startsWith("/animus/studio")) return false;
  if (pathname.startsWith("/animus/imagine")) return false;
  if (pathname.startsWith("/replay")) return false;
  return (
    pathname === "/" ||
    pathname.startsWith("/science") ||
    pathname.startsWith("/method") ||
    pathname.startsWith("/research") ||
    pathname.startsWith("/reports") ||
    pathname === "/profile" ||
    pathname.startsWith("/animus/profile") ||
    pathname.startsWith("/animus/observatory")
  );
}
