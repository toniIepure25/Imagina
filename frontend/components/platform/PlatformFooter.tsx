import Link from "next/link";
import { PLATFORM_BOUNDARY } from "@/lib/claims";

export default function PlatformFooter() {
  return (
    <footer className="mt-auto border-t border-surface-border bg-background/70 px-4 py-6 text-xs leading-6 text-foreground/45 print:hidden">
      <div className="mx-auto flex w-full max-w-[1500px] flex-wrap items-start justify-between gap-5">
        <div className="max-w-2xl">
          <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-foreground/40">
            IMAGINA · local-first research prototype
          </p>
          <p className="mt-1.5 max-w-xl text-foreground/45">{PLATFORM_BOUNDARY}</p>
        </div>
        <nav aria-label="Footer" className="flex flex-wrap gap-x-4 gap-y-1 text-foreground/55">
          <Link href="/animus" className="hover:text-foreground">
            Studio
          </Link>
          <Link href="/science" className="hover:text-foreground">
            Science
          </Link>
          <Link href="/method" className="hover:text-foreground">
            Method &amp; claims
          </Link>
          <Link href="/research/design" className="hover:text-foreground">
            Design a study
          </Link>
          <Link href="/animus/about" className="hover:text-foreground">
            Boundaries
          </Link>
          <Link href="/research" className="hover:text-foreground">
            Lab
          </Link>
        </nav>
      </div>
    </footer>
  );
}
