import type { ReactNode } from "react";

export default function AsyncState({
  kind,
  title,
  body,
  action,
}: {
  kind: "loading" | "empty" | "error";
  title: string;
  body?: string;
  action?: ReactNode;
}) {
  const label = kind === "loading" ? "Loading" : kind === "error" ? "Unavailable" : "Nothing here yet";
  return (
    <div
      className={`rounded-xl border p-6 ${
        kind === "error" ? "border-danger/25 bg-danger/[0.04]" : "border-surface-border bg-surface/25"
      }`}
      role={kind === "error" ? "alert" : "status"}
      aria-busy={kind === "loading" || undefined}
    >
      <div className={`mono-label ${kind === "error" ? "text-danger/80" : "text-foreground/40"}`}>{label}</div>
      <div className="mt-2 text-base font-medium text-foreground/85">{title}</div>
      {body ? <p className="mt-2 max-w-2xl text-sm leading-6 text-foreground/55">{body}</p> : null}
      {action ? <div className="mt-4 flex flex-wrap gap-2">{action}</div> : null}
    </div>
  );
}
