"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { LAB_NAV, PRIMARY_NAV, isLabRoute, isNavLinkActive } from "@/lib/navigation";
import { useGlassBox } from "@/components/evidence/GlassBoxContext";
import GlassBoxToggle from "@/components/evidence/GlassBoxToggle";
import ClaimBadge from "./ClaimBadge";
import PlatformCommandPalette from "./PlatformCommandPalette";
import type { PlatformCommand } from "./commandTypes";

function NavLinkItem({
  href,
  label,
  active,
  onNavigate,
}: {
  href: string;
  label: string;
  active: boolean;
  onNavigate?: () => void;
}) {
  return (
    <Link
      href={href}
      onClick={onNavigate}
      aria-current={active ? "page" : undefined}
      className={`relative inline-flex min-h-9 items-center px-3 text-sm transition-colors ${
        active
          ? "text-foreground"
          : "text-foreground/55 hover:text-foreground"
      }`}
    >
      {label}
      {active ? (
        <span
          className="absolute inset-x-3 -bottom-[11px] h-px bg-gradient-to-r from-transparent via-accent-glow/70 to-transparent"
          aria-hidden="true"
        />
      ) : null}
    </Link>
  );
}

export default function PlatformHeader({ level, status }: { level?: number; status?: string }) {
  const pathname = usePathname();
  const router = useRouter();
  const { enabled: evidenceEnabled, setPreference: setEvidencePreference } = useGlassBox();
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const labActive = isLabRoute(pathname);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setPaletteOpen((current) => !current);
      }
      if (event.key === "Escape") setMobileOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const actions = useMemo<PlatformCommand[]>(() => {
    const go = (href: string) => () => router.push(href);
    const routes = [...PRIMARY_NAV, ...LAB_NAV].map((link) => ({
      id: `route-${link.href.replaceAll("/", "-")}`,
      label: link.label,
      detail: link.description,
      group: LAB_NAV.some((item) => item.href === link.href) ? "Lab" : "Go",
      keywords: `${link.keywords ?? ""} ${link.href}`,
      run: go(link.href),
    }));
    return [
      ...routes,
      {
        id: "evidence-toggle",
        label: evidenceEnabled ? "Hide evidence marks" : "Show evidence marks",
        detail: "Toggle provenance badges across the platform",
        group: "Evidence",
        keywords: "glass box provenance source method",
        run: () => setEvidencePreference(evidenceEnabled ? "off" : "on"),
      },
      {
        id: "route-method",
        label: "Method & Claim Atlas",
        detail: "Every metric, source, method, uncertainty, and boundary",
        group: "Evidence",
        keywords: "provenance registry audit claim",
        run: go("/method"),
      },
      {
        id: "route-study-design",
        label: "Design a study",
        detail: "Build a locked, exportable N-of-1 plan",
        group: "Research",
        keywords: "preregistration n-of-1 protocol study",
        run: go("/research/design"),
      },
      {
        id: "route-boundaries",
        label: "Scientific boundaries",
        detail: "What the platform does, does not do, and cannot claim",
        group: "Go",
        keywords: "claims limits ethics validation",
        run: go("/science"),
      },
    ];
  }, [evidenceEnabled, router, setEvidencePreference]);

  return (
    <>
      <a href="#main" className="skip-link">
        Skip to content
      </a>
      <header className="sticky top-0 z-50 border-b border-surface-border bg-background/85 backdrop-blur-xl print:hidden">
        <div className="mx-auto flex h-14 w-full max-w-[1500px] items-center gap-4 px-4 md:px-6">
          <Link href="/" className="group flex min-w-0 items-center gap-2.5" aria-label="IMAGINA home">
            <span
              className="relative grid h-8 w-8 shrink-0 place-items-center rounded-full border border-lumen-bone/15 bg-lumen-bone/[0.03]"
              aria-hidden="true"
            >
              <span className="absolute inset-[3px] rounded-full border border-dashed border-accent-glow/25 transition-transform duration-700 group-hover:rotate-90" />
              <span className="h-1.5 w-1.5 rounded-full bg-accent-glow shadow-[0_0_16px_rgba(124,240,207,0.85)]" />
            </span>
            <span className="min-w-0 leading-none">
              <span className="block text-xs font-semibold tracking-[0.24em] text-foreground/90">IMAGINA</span>
              <span className="mt-1 block font-mono text-[11px] tracking-[0.2em] text-accent-glow/60">
                RESEARCH PLATFORM
              </span>
            </span>
          </Link>

          <nav aria-label="Primary" className="hidden items-center gap-0.5 lg:flex">
            {PRIMARY_NAV.map((link) => (
              <NavLinkItem
                key={link.href}
                href={link.href}
                label={link.label}
                active={isNavLinkActive(pathname, link.href)}
              />
            ))}
            <details className="group relative">
              <summary
                className={`inline-flex min-h-9 cursor-pointer list-none items-center px-3 text-sm transition-colors [&::-webkit-details-marker]:hidden ${
                  labActive
                    ? "text-foreground"
                    : "text-foreground/55 hover:text-foreground"
                }`}
              >
                Lab
                <span className="ml-1.5 text-[11px] text-foreground/35 group-open:rotate-180" aria-hidden="true">
                  ▾
                </span>
              </summary>
              <div className="absolute left-0 top-10 z-50 w-80 rounded-xl border border-white/12 bg-[#090b14] p-2 shadow-2xl">
                <p className="px-3 py-2 font-mono text-[11px] uppercase tracking-[0.16em] text-foreground/35">
                  Technical preview
                </p>
                {LAB_NAV.map((link) => (
                  <Link
                    key={link.href}
                    href={link.href}
                    className={`block rounded-lg px-3 py-2 transition-colors ${
                      isNavLinkActive(pathname, link.href) ? "bg-accent-glow/[0.08]" : "hover:bg-white/[0.04]"
                    }`}
                  >
                    <span className="block text-sm text-foreground/85">{link.label}</span>
                    <span className="mt-0.5 block text-xs leading-5 text-foreground/45">{link.description}</span>
                  </Link>
                ))}
              </div>
            </details>
          </nav>

          <div className="ml-auto flex items-center gap-2">
            {level !== undefined ? (
              <span className="hidden rounded-full border border-white/10 px-2.5 py-1 font-mono text-[11px] text-foreground/55 sm:inline-flex">
                Level {level}
              </span>
            ) : null}
            {status ? (
              <span className="hidden rounded-full border border-signal/25 bg-signal/[0.06] px-2.5 py-1 font-mono text-[11px] text-signal/75 sm:inline-flex">
                {status}
              </span>
            ) : null}
            <ClaimBadge className="hidden xl:inline-flex" />
            <GlassBoxToggle compact />
            <button
              type="button"
              onClick={() => setPaletteOpen(true)}
              aria-label="Open command palette"
              aria-haspopup="dialog"
              className="group inline-flex min-h-9 items-center gap-2 border border-white/10 bg-white/[0.025] px-2.5 text-xs text-foreground/50 transition-colors hover:border-accent-glow/25 hover:text-foreground/85"
            >
              <span className="hidden sm:inline">Jump to</span>
              <kbd className="rounded border border-white/10 bg-black/25 px-1.5 py-0.5 font-mono text-[11px] text-foreground/40 group-hover:text-foreground/65">
                ⌘K
              </kbd>
            </button>
            <button
              type="button"
              onClick={() => setMobileOpen((current) => !current)}
              aria-expanded={mobileOpen}
              aria-controls="platform-mobile-nav"
              aria-label={mobileOpen ? "Close navigation" : "Open navigation"}
              className="grid h-11 w-11 shrink-0 place-items-center rounded-full border border-white/10 text-foreground/60 transition-colors hover:border-accent-glow/30 hover:text-foreground lg:hidden"
            >
              <span aria-hidden="true">{mobileOpen ? "✕" : "☰"}</span>
            </button>
          </div>
        </div>

        {mobileOpen ? (
          <nav
            id="platform-mobile-nav"
            aria-label="Mobile navigation"
            className="max-h-[calc(100dvh-3.5rem)] overflow-y-auto border-t border-white/8 px-4 py-3 lg:hidden"
          >
            <div className="grid gap-1 sm:grid-cols-2">
              {PRIMARY_NAV.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={() => setMobileOpen(false)}
                  aria-current={isNavLinkActive(pathname, link.href) ? "page" : undefined}
                  className="rounded-lg px-3 py-2.5 text-sm text-foreground/75 hover:bg-white/[0.04]"
                >
                  {link.label}
                </Link>
              ))}
            </div>
            <p className="mt-4 px-3 font-mono text-[11px] uppercase tracking-[0.16em] text-foreground/35">
              Lab · technical preview
            </p>
            <div className="mt-1 grid gap-1 sm:grid-cols-2">
              {LAB_NAV.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={() => setMobileOpen(false)}
                  aria-current={isNavLinkActive(pathname, link.href) ? "page" : undefined}
                  className="rounded-lg px-3 py-2.5 text-sm text-foreground/70 hover:bg-white/[0.04]"
                >
                  {link.label}
                </Link>
              ))}
            </div>
          </nav>
        ) : null}
      </header>

      <PlatformCommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} actions={actions} />
    </>
  );
}
