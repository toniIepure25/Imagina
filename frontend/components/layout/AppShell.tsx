import { ReactNode } from "react";
import PlatformFooter from "@/components/platform/PlatformFooter";
import PlatformHeader from "@/components/platform/PlatformHeader";

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
    <div className="platform-root flex min-h-screen flex-col">
      <PlatformHeader level={level} status={status} />
      <main id="main" tabIndex={-1} className="flex flex-1 flex-col outline-none">
        {children}
      </main>
      <PlatformFooter />
    </div>
  );
}
