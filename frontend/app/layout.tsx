import type { Metadata } from "next";
import GlassBoxProvider from "@/components/evidence/GlassBoxProvider";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "IMAGINA — ANIMUS Studio",
    template: "%s · IMAGINA",
  },
  description:
    "A local-first research platform for deliberate imagination: describe a scene, see a procedural candidate, correct it, and converge — without decoding thoughts or generating images from a model.",
  applicationName: "IMAGINA",
  robots: { index: false, follow: false },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased dark">
      <body className="min-h-screen flex flex-col bg-background text-foreground">
        <GlassBoxProvider>{children}</GlassBoxProvider>
      </body>
    </html>
  );
}
