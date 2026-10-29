import type { HTMLAttributes, ReactNode } from "react";

export default function HudLabel({
  className = "",
  children,
  ...props
}: HTMLAttributes<HTMLSpanElement> & { children: ReactNode }) {
  return (
    <span className={`hud-label ${className}`} {...props}>
      {children}
    </span>
  );
}
