import Link from "next/link";
import Badge from "../common/Badge";

const NAV = [
  ["Command Center", "/multimodal"],
  ["Animus", "/animus"],
  ["Worlds", "/animus/worlds"],
  ["Session", "/session"],
  ["Replay", "/replay"],
  ["Profile", "/profile"],
  ["Experiments", "/experiments"],
  ["Science", "/science"],
];

export default function Header({
  level,
  status,
}: {
  level?: number;
  status?: string;
}) {
  return (
    <header className="sticky top-0 z-40 flex items-center justify-between px-6 py-3 border-b border-surface-border bg-background/78 backdrop-blur-md">
      <Link href="/" className="group flex items-baseline gap-2" aria-label="IMAGINA home">
        <span className="text-sm font-semibold tracking-[0.24em] glow-text">IMAGINA</span>
        <span className="font-mono text-[11px] uppercase tracking-[0.2em] text-accent-glow/55">research</span>
      </Link>
      <nav className="hidden md:flex items-center gap-3 text-xs text-foreground/55">
        {NAV.map(([label, href]) => (
          <Link key={href} href={href} className="hover:text-foreground transition-colors">
            {label}
          </Link>
        ))}
      </nav>
      <div className="flex items-center gap-3">
        {level !== undefined && (
          <Badge>Level {level}</Badge>
        )}
        {status && (
          <Badge color={status === "running" || status === "connected" ? "bg-signal/20 text-signal" : "bg-foreground/10 text-foreground/50"}>
            {status}
          </Badge>
        )}
      </div>
    </header>
  );
}
