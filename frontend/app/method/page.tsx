import type { Metadata } from "next";
import AppShell from "@/components/layout/AppShell";
import MethodAtlas from "@/components/evidence/MethodAtlas";

export const metadata: Metadata = {
  title: "Method & Claim Atlas",
  description:
    "A local catalogue of IMAGINA's measured, derived, simulated, and narrative evidence, including sources, uncertainty, and hard boundaries.",
};

export default function MethodPage() {
  return (
    <AppShell>
      <MethodAtlas />
    </AppShell>
  );
}
