import type { Metadata } from "next";
import ImagineLab from "@/components/imagine/ImagineLab";

export const metadata: Metadata = {
  title: "IMAGINA Imagine — adaptive first-person scene lab",
  description:
    "Describe a scene, shape 16 derived conditioning dimensions, and walk a symbolic first-person preview. The diffusion lane is fail-closed until an A100 worker is attached.",
};

export default function ImaginePage() {
  return <ImagineLab />;
}
