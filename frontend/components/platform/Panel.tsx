import type { ReactNode } from "react";

export default function Panel({
  children,
  className = "",
  as: Tag = "section",
}: {
  children: ReactNode;
  className?: string;
  as?: "section" | "div" | "article";
}) {
  return (
    <Tag className={`rounded-xl border border-surface-border bg-surface/35 ${className}`}>
      {children}
    </Tag>
  );
}
