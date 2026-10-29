import type { Metadata } from "next";
import AppShell from "@/components/layout/AppShell";
import ParticipantRunner from "@/components/research/ParticipantRunner";

export const metadata: Metadata = {
  title: "Participant Mode",
  description:
    "A local demonstration of the imagery self-report task: consent, three trials, timing, and an optional local JSON export. No data is sent.",
};

export default function ParticipantPage() {
  return (
    <AppShell>
      <ParticipantRunner />
    </AppShell>
  );
}
