import type { ReactNode } from "react";

export default function DossierSheet({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return <div className={`dossier-sheet mx-auto w-full max-w-6xl ${className}`}>{children}</div>;
}
