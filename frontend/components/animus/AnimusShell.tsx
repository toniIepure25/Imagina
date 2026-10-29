"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import AnimusCommandPalette from "./AnimusCommandPalette";
import { AnimusCommandProvider, useOptionalAnimusCommands } from "./AnimusCommandRegistry";
import ShortcutOverlay from "./ShortcutOverlay";

export type AnimusSection =
  | "home"
  | "studio"
  | "imagine"
  | "practice"
  | "interview"
  | "observatory"
  | "worlds"
  | "profile"
  | "about";

const PRIMARY = [
  { id: "studio", label: "Studio", href: "/animus" },
  { id: "imagine", label: "Imagine", href: "/animus/imagine" },
  { id: "worlds", label: "Worlds", href: "/animus/worlds" },
  { id: "profile", label: "Profile", href: "/animus/profile" },
  { id: "about", label: "Boundaries", href: "/animus/about" },
] as const;

const SESSION_LINKS = [
  { id: "studio", label: "Studio" },
  { id: "practice", label: "Recall" },
  { id: "interview", label: "Beliefs" },
  { id: "observatory", label: "Threshold" },
] as const;

function isPrimaryActive(section: AnimusSection, id: string): boolean {
  if (section === "studio" || section === "home") return id === "studio";
  return section === id;
}

export default function AnimusShell({
  children,
  sessionId,
  active,
  workspace = false,
}: {
  children: ReactNode;
  sessionId?: string;
  active?: AnimusSection;
  workspace?: boolean;
}) {
  const pathname = usePathname();
  const existingCommands = useOptionalAnimusCommands();
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  const section: AnimusSection =
    active ??
    (pathname?.startsWith("/animus/studio")
      ? "studio"
      : pathname?.startsWith("/animus/imagine")
        ? "imagine"
        : pathname?.startsWith("/animus/practice")
        ? "practice"
        : pathname?.startsWith("/animus/interview")
          ? "interview"
          : pathname?.startsWith("/animus/observatory")
            ? "observatory"
            : pathname?.startsWith("/animus/worlds")
              ? "worlds"
              : pathname?.startsWith("/animus/profile")
                ? "profile"
                : pathname?.startsWith("/animus/about")
                  ? "about"
                  : "home");

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setPaletteOpen((current) => !current);
      }
      if (event.key === "?" && !event.metaKey && !event.ctrlKey && !event.altKey) {
        const target = event.target as HTMLElement | null;
        if (target?.closest("input, textarea, select, [contenteditable='true']")) return;
        event.preventDefault();
        setShortcutsOpen(true);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const frame = (
    <div className={`animus-root flex flex-col ${workspace ? "min-h-dvh xl:h-dvh xl:overflow-hidden" : "min-h-dvh"}`}>
      <a href="#animus-main" className="skip-link">
        Skip to content
      </a>

      <header className="relative z-50 border-b border-white/[0.08] bg-[#05070a]/88 backdrop-blur-xl">
        <div className="mx-auto flex h-14 w-full max-w-[1500px] items-center gap-4 px-4 md:px-6">
          <Link href="/animus" className="group flex min-w-0 items-center gap-2.5" aria-label="IMAGINA ANIMUS home">
            <span
              className="relative grid h-8 w-8 shrink-0 place-items-center rounded-full border border-lumen-bone/15 bg-lumen-bone/[0.03]"
              aria-hidden="true"
            >
              <span className="absolute inset-[3px] rounded-full border border-dashed border-accent-glow/25 transition-transform duration-700 group-hover:rotate-90" />
              <span className="h-1.5 w-1.5 rounded-full bg-accent-glow shadow-[0_0_16px_rgba(124,240,207,0.85)]" />
            </span>
            <span className="min-w-0 leading-none">
              <span className="block text-[11px] font-semibold tracking-[0.26em] text-foreground/90">IMAGINA</span>
              <span className="mt-1 block font-mono text-[11px] tracking-[0.24em] text-accent-glow/60">
                ANIMUS / LUMEN
              </span>
            </span>
          </Link>

          <nav aria-label="ANIMUS sections" className="hidden items-center gap-1 md:flex">
            {PRIMARY.map((item) => {
              const current = isPrimaryActive(section, item.id);
              return (
                <Link
                  key={item.id}
                  href={item.id === "studio" && sessionId ? `/animus/studio/${sessionId}` : item.href}
                  aria-current={current ? "page" : undefined}
                  className={`relative inline-flex min-h-9 items-center px-3 text-[11px] tracking-[0.02em] transition-colors ${
                    current ? "text-foreground" : "text-foreground/45 hover:text-foreground/85"
                  }`}
                >
                  {item.label}
                  {current && (
                    <span className="absolute inset-x-3 -bottom-[11px] h-px bg-gradient-to-r from-transparent via-accent-glow/80 to-transparent" />
                  )}
                </Link>
              );
            })}
          </nav>

          <div className="ml-auto flex items-center gap-2">
            <Link
              href="/"
              className="hidden text-[11px] text-foreground/35 transition-colors hover:text-foreground/80 sm:inline-flex"
            >
              Platform home
            </Link>
            <span
              className="hidden items-center gap-1.5 border border-emerald-300/15 bg-emerald-300/[0.04] px-2.5 py-1 font-mono text-[11px] uppercase tracking-[0.14em] text-emerald-200/65 sm:inline-flex"
              title="Local SQLite · no accounts · no telemetry"
            >
              <span className="h-1 w-1 rounded-full bg-emerald-300/80" aria-hidden="true" />
              local only
            </span>
            <button
              type="button"
              onClick={() => setPaletteOpen(true)}
              aria-label="Open command palette"
              aria-haspopup="dialog"
              className="group flex min-h-9 items-center gap-2 border border-white/10 bg-white/[0.025] px-2.5 text-[11px] text-foreground/45 transition-colors hover:border-accent-glow/30 hover:text-foreground/85"
            >
              <span>Jump to</span>
              <kbd className="rounded border border-white/10 bg-black/25 px-1.5 py-0.5 font-mono text-[11px] text-foreground/30 group-hover:text-foreground/55">
                ⌘K
              </kbd>
            </button>
          </div>
        </div>

        <nav
          aria-label="ANIMUS sections on small screens"
          className="flex items-center gap-1 overflow-x-auto border-t border-white/[0.05] px-4 py-1.5 md:hidden [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
        >
          {PRIMARY.map((item) => {
            const current = isPrimaryActive(section, item.id);
            return (
              <Link
                key={item.id}
                href={item.id === "studio" && sessionId ? `/animus/studio/${sessionId}` : item.href}
                aria-current={current ? "page" : undefined}
                className={`shrink-0 rounded-full px-2.5 py-1 text-[11px] ${
                  current ? "bg-white/[0.07] text-foreground" : "text-foreground/40"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </header>

      {sessionId && (
        <div className="relative z-40 border-b border-white/[0.06] bg-[#070911]/70">
          <div className="mx-auto flex h-9 w-full max-w-[1500px] items-center gap-2 overflow-x-auto px-4 md:px-6 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
            <span className="shrink-0 font-mono text-[11px] uppercase tracking-[0.22em] text-foreground/25">
              session
            </span>
            {SESSION_LINKS.map((item) => {
              const current = section === item.id;
              return (
                <Link
                  key={item.id}
                  href={`/animus/${item.id}/${sessionId}`}
                  aria-current={current ? "page" : undefined}
                  className={`shrink-0 rounded-full px-2.5 py-1 text-[11px] transition-colors ${
                    current
                      ? "bg-accent-glow/[0.08] text-accent-glow/85"
                      : "text-foreground/40 hover:bg-white/[0.04] hover:text-foreground/70"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
            <span className="ml-auto hidden shrink-0 font-mono text-[11px] uppercase tracking-[0.14em] text-foreground/20 sm:inline">
              L1 · behavioural-assisted
            </span>
          </div>
        </div>
      )}

      <main id="animus-main" className={workspace ? "flex-1 xl:min-h-0 xl:overflow-hidden" : "flex-1"}>
        {children}
      </main>

      {!workspace && (
        <footer className="border-t border-white/[0.06] bg-black/20">
          <div className="mx-auto flex w-full max-w-6xl flex-col gap-4 px-6 py-7 sm:flex-row sm:items-end sm:justify-between">
            <div className="max-w-2xl">
              <p className="font-mono text-[11px] uppercase tracking-[0.24em] text-foreground/25">
                IMAGINA · local-first imagination research
              </p>
              <p className="mt-2 text-[11px] leading-relaxed text-foreground/35">
                ANIMUS is a behavioural imagery scaffold. It does not decode thoughts or dreams, does not measure
                neural content, and does not generate images with a model. The claim ceiling is L1
                (behavioural-assisted); every scene is a symbolic preview.
              </p>
            </div>
            <div className="flex shrink-0 flex-wrap gap-x-4 gap-y-1 text-[11px] text-foreground/35">
              <Link href="/" className="hover:text-foreground">
                Platform home
              </Link>
              <Link href="/science" className="hover:text-foreground">
                Scientific framing
              </Link>
              <Link href="/animus/about" className="hover:text-foreground">
                Scientific boundaries
              </Link>
              <Link href="/animus/profile" className="hover:text-foreground">
                Profile
              </Link>
              <Link href="/animus/worlds" className="hover:text-foreground">
                Worlds
              </Link>
            </div>
          </div>
        </footer>
      )}

      <AnimusCommandPalette
        key={paletteOpen ? "palette-open" : "palette-closed"}
        open={paletteOpen}
        sessionId={sessionId}
        onClose={() => setPaletteOpen(false)}
      />
      <ShortcutOverlay open={shortcutsOpen} onClose={() => setShortcutsOpen(false)} />
    </div>
  );

  return existingCommands ? frame : <AnimusCommandProvider>{frame}</AnimusCommandProvider>;
}
