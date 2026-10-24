import type { Metadata } from "next";
import StudioClient from "@/components/animus/StudioClient";

export const metadata: Metadata = {
  title: "ANIMUS Studio — closed-loop imagination amplifier",
  description:
    "Describe a scene, see a procedural candidate, correct it, lock what is right, and keep or explore.",
};

export default async function StudioPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = await params;
  return <StudioClient sessionId={sessionId} />;
}
