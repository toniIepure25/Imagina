"use client";

import { ReactNode } from "react";
import Header from "./Header";
import Footer from "./Footer";

export default function AppShell({
  children,
  level,
  status,
}: {
  children: ReactNode;
  level?: number;
  status?: string;
}) {
  return (
    <div className="flex flex-col min-h-screen">
      <Header level={level} status={status} />
      <main className="flex-1 flex">{children}</main>
      <Footer />
    </div>
  );
}
