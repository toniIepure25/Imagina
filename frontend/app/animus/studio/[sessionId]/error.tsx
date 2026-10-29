"use client";

import Link from "next/link";
import { useEffect } from "react";
import Button from "@/components/common/Button";
import AnimusShell from "@/components/animus/AnimusShell";

export default function StudioError({
  error,
  unstable_retry,
}: {
  error: Error & { digest?: string };
  unstable_retry: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <AnimusShell active="studio" workspace>
      <div className="flex min-h-[70vh] flex-1 items-center justify-center p-6">
        <section className="glass max-w-md space-y-4 p-6 text-center" role="alert">
          <h1 className="text-lg font-semibold">The studio stopped unexpectedly</h1>
          <p className="text-xs leading-relaxed text-foreground/50">
            Your scene is saved locally after every accepted change. Retry the studio, or return to the
            scene list without losing durable history.
          </p>
          {error.digest && (
            <p className="text-[11px] text-foreground/30">
              Reference: <code>{error.digest}</code>
            </p>
          )}
          <div className="flex justify-center gap-2">
            <Button size="sm" variant="secondary" onClick={() => unstable_retry()}>
              Try again
            </Button>
            <Link
              href="/animus"
              className="rounded-lg border border-surface-border px-3 py-1.5 text-sm text-foreground/80 transition-colors hover:border-accent/50 hover:bg-surface"
            >
              Back to Animus
            </Link>
          </div>
        </section>
      </div>
    </AnimusShell>
  );
}
