import Link from "next/link";
import AppShell from "@/components/layout/AppShell";

export default function NotFound() {
  return (
    <AppShell>
      <div className="mx-auto grid w-full max-w-3xl flex-1 place-items-center px-6 py-20">
        <div className="w-full rounded-2xl border border-surface-border bg-surface/35 p-8">
          <p className="mono-label text-accent-glow/70">404 · no such instrument</p>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight">That route is not part of this local build.</h1>
          <p className="mt-3 max-w-xl text-sm leading-7 text-foreground/55">
            Nothing was deleted. The path may be mistyped, or the view may belong to an older experiment. Use the
            stable entry points below.
          </p>
          <div className="mt-6 flex flex-wrap gap-2">
            <Link
              href="/animus"
              className="inline-flex min-h-10 items-center rounded-lg bg-accent px-4 text-sm font-medium text-white hover:bg-accent-glow hover:text-background"
            >
              Open Studio
            </Link>
            <Link
              href="/session"
              className="inline-flex min-h-10 items-center rounded-lg border border-surface-border px-4 text-sm text-foreground/70 hover:text-foreground"
            >
              Start a session
            </Link>
            <Link
              href="/science"
              className="inline-flex min-h-10 items-center rounded-lg px-4 text-sm text-foreground/50 hover:text-foreground"
            >
              Scientific boundaries
            </Link>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
