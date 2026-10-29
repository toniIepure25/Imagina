export default function Loading() {
  return (
    <main id="main" className="grid min-h-screen place-items-center bg-[#07090d] px-6 py-16 text-[#e8edf4]">
      <div className="w-full max-w-xl" role="status" aria-live="polite" aria-busy="true">
        <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-[#8fc7ff]/70">Local interface</p>
        <div className="mt-4 h-3 w-2/3 animate-pulse rounded bg-white/10" />
        <div className="mt-3 h-3 w-1/2 animate-pulse rounded bg-white/[0.07]" />
        <p className="mt-5 text-sm text-white/40">Loading this view from the local backend…</p>
      </div>
    </main>
  );
}
