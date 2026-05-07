import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "IMAGINA V1 — Dream Corridor Scene Stabilizer",
  description:
    "A research prototype for closed-loop mental imagery training. Estimates proxy metrics for attention, vividness, and behavioral stability.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased dark">
      <body className="min-h-screen flex flex-col bg-background text-foreground">
        {children}
      </body>
    </html>
  );
}
