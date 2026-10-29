"use client";

import Button from "@/components/common/Button";
import ButtonLink from "@/components/common/ButtonLink";
import AnimusShell, { type AnimusSection } from "./AnimusShell";

export function AnimusRouteSkeleton({
  section,
  label,
  workspace = false,
}: {
  section: AnimusSection;
  label: string;
  workspace?: boolean;
}) {
  return (
    <AnimusShell active={section} workspace={workspace}>
      <div className="mx-auto flex min-h-[55vh] w-full max-w-5xl flex-col justify-center px-4 py-10" aria-busy="true">
        <div className="animate-pulse space-y-4">
          <div className="h-3 w-24 rounded bg-white/8" />
          <div className="h-8 w-2/3 rounded bg-white/8" />
          <div className="h-3 w-1/2 rounded bg-white/6" />
          <div className="mt-8 h-56 rounded-xl border border-white/8 bg-white/[0.025]" />
        </div>
        <p role="status" className="mt-6 font-mono text-[11px] uppercase tracking-[0.2em] text-foreground/30">
          {label}
        </p>
      </div>
    </AnimusShell>
  );
}

export function AnimusRouteError({
  section,
  title,
  error,
  retry,
}: {
  section: AnimusSection;
  title: string;
  error: Error & { digest?: string };
  retry: () => void;
}) {
  return (
    <AnimusShell active={section}>
      <div className="mx-auto flex min-h-[60vh] w-full max-w-lg flex-col justify-center px-4 py-10">
        <div className="rounded-xl border border-white/12 bg-white/[0.025] p-6" role="alert">
          <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-lock/70">Local instrument error</p>
          <h1 className="mt-2 font-display text-2xl text-foreground/90">{title}</h1>
          <p className="mt-2 text-[11px] leading-relaxed text-foreground/45">
            {error.message || "The segment could not render. Your saved scenes and local profile are unchanged."}
          </p>
          {error.digest ? (
            <p className="mt-2 font-mono text-[11px] text-foreground/25">digest · {error.digest}</p>
          ) : null}
          <div className="mt-5 flex flex-wrap gap-2">
            <Button size="sm" variant="secondary" onClick={() => retry()}>
              Try again
            </Button>
            <ButtonLink href="/animus" size="sm" variant="ghost">
              Back to Animus
            </ButtonLink>
          </div>
        </div>
      </div>
    </AnimusShell>
  );
}
