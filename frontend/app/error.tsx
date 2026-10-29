"use client";

import Link from "next/link";
import { useEffect } from "react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <main id="main" className="grid min-h-screen place-items-center bg-[#07090d] px-6 py-16 text-[#e8edf4]">
      <div className="w-full max-w-xl rounded-2xl border border-white/12 bg-white/[0.03] p-6">
        <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-[#e8b45a]/80">Local boundary</p>
        <h1 className="mt-3 text-2xl font-semibold tracking-tight">This view could not be rendered</h1>
        <p className="mt-3 text-sm leading-7 text-white/55">
          The local interface hit an unexpected state. Your data is still on this machine. Retry the view, or return to a
          stable entry point.
        </p>
        {error.digest ? (
          <p className="mt-3 font-mono text-[11px] text-white/35">reference · {error.digest}</p>
        ) : null}
        <div className="mt-6 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={reset}
            className="inline-flex min-h-10 items-center rounded-lg bg-[#5c7cfa] px-4 text-sm font-medium text-white hover:bg-[#8fc7ff] hover:text-[#07090d]"
          >
            Retry this view
          </button>
          <Link
            href="/"
            className="inline-flex min-h-10 items-center rounded-lg border border-white/15 px-4 text-sm text-white/70 hover:text-white"
          >
            Return home
          </Link>
          <Link
            href="/science"
            className="inline-flex min-h-10 items-center rounded-lg px-4 text-sm text-white/50 hover:text-white"
          >
            Scientific boundaries
          </Link>
        </div>
      </div>
    </main>
  );
}
