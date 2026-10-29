"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";

export default function SaveWorldDialog({
  open,
  defaultName,
  busy,
  onClose,
  onSave,
}: {
  open: boolean;
  defaultName: string;
  busy: boolean;
  onClose: () => void;
  onSave: (name: string, description: string) => Promise<boolean>;
}) {
  const [name, setName] = useState(defaultName);
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!open) return;
    const timer = window.setTimeout(() => {
      inputRef.current?.focus();
      inputRef.current?.select();
    }, 20);
    return () => window.clearTimeout(timer);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose, open]);

  if (!open) return null;

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!name.trim()) {
      setError("Give the world a name.");
      return;
    }
    setError(null);
    const saved = await onSave(name.trim(), description.trim());
    if (!saved) setError("The world could not be saved. Your scene is unchanged.");
  };

  return (
    <div
      className="fixed inset-0 z-[125] flex items-start justify-center bg-black/65 px-4 pt-[14vh] backdrop-blur-sm"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <form
        role="dialog"
        aria-modal="true"
        aria-labelledby="save-world-title"
        data-testid="save-world-dialog"
        onSubmit={(event) => void submit(event)}
        className="w-full max-w-md rounded-xl border border-white/12 bg-[#0b0d10] p-5 shadow-2xl"
      >
        <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-signal/60">Local library</p>
        <h2 id="save-world-title" className="mt-1 font-display text-xl text-foreground/90">
          Keep this world
        </h2>
        <p className="mt-1 text-[11px] leading-relaxed text-foreground/40">
          A world is a complete scene graph on this machine. It is not a rendered image and nothing is uploaded.
        </p>
        <label className="mt-4 block text-[11px] text-foreground/45">
          Name
          <input
            ref={inputRef}
            value={name}
            onChange={(event) => setName(event.target.value)}
            maxLength={120}
            className="mt-1 w-full rounded border border-white/12 bg-white/[0.03] px-2.5 py-2 text-[12px] text-foreground/80 focus:border-signal/40 focus:outline-none"
          />
        </label>
        <label className="mt-3 block text-[11px] text-foreground/45">
          Description <span className="text-foreground/25">optional</span>
          <textarea
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            rows={3}
            maxLength={500}
            className="mt-1 w-full resize-none rounded border border-white/12 bg-white/[0.03] px-2.5 py-2 text-[11px] leading-relaxed text-foreground/75 focus:border-signal/40 focus:outline-none"
          />
        </label>
        {error ? <p role="alert" className="mt-2 text-[11px] text-red-300/85">{error}</p> : null}
        <div className="mt-4 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            disabled={busy}
            className="rounded border border-white/12 px-3 py-1.5 text-[11px] text-foreground/45 hover:text-foreground disabled:opacity-40"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={busy || !name.trim()}
            className="rounded border border-signal/40 bg-signal/10 px-3 py-1.5 text-[11px] text-signal disabled:opacity-40"
          >
            {busy ? "Saving…" : "Save locally"}
          </button>
        </div>
      </form>
    </div>
  );
}
