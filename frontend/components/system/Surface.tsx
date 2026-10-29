import type { HTMLAttributes, ReactNode } from "react";

type SurfaceTone = "stage" | "tray" | "rail";

const tones: Record<SurfaceTone, string> = {
  stage: "surface-stage",
  tray: "surface-tray",
  rail: "surface-rail",
};

export default function Surface({
  tone = "tray",
  className = "",
  children,
  ...props
}: HTMLAttributes<HTMLDivElement> & {
  tone?: SurfaceTone;
  children: ReactNode;
}) {
  return (
    <div className={`${tones[tone]} ${className}`} {...props}>
      {children}
    </div>
  );
}
