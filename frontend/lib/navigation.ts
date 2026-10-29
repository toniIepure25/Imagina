export type NavLink = {
  href: string;
  label: string;
  description: string;
  keywords?: string;
};

export type NavGroup = {
  id: string;
  label: string;
  description: string;
  links: NavLink[];
};

export const PRIMARY_NAV: NavLink[] = [
  {
    href: "/animus",
    label: "Studio",
    description: "Author, compare, and inspect a symbolic scene",
    keywords: "animus scene versions trace",
  },
  {
    href: "/session",
    label: "Sessions",
    description: "Run a closed-loop imagery practice session",
    keywords: "practice train corridor",
  },
  {
    href: "/replay",
    label: "Replay",
    description: "Review a deterministic session replay",
    keywords: "timeline history playback",
  },
  {
    href: "/science",
    label: "Science",
    description: "Methods, proxy metrics, and boundaries",
    keywords: "claims limitations methods",
  },
  {
    href: "/profile",
    label: "Profile",
    description: "Local measurement ledger across sessions",
    keywords: "progress longitudinal measurements",
  },
];

export const LAB_NAV: NavLink[] = [
  {
    href: "/multimodal",
    label: "Command center",
    description: "Live multimodal signals and controller decisions",
    keywords: "live eeg ecg eda fnirs devices",
  },
  {
    href: "/experiments",
    label: "Experiments",
    description: "Protocols, runs, and linked sessions",
    keywords: "research protocol run",
  },
  {
    href: "/datasets",
    label: "Datasets",
    description: "Local dataset readiness and provenance",
    keywords: "data validation openmiir",
  },
  {
    href: "/method",
    label: "Method & claims",
    description: "Every metric, its source, and what it cannot show",
    keywords: "evidence provenance glass box claims audit",
  },
  {
    href: "/research",
    label: "Research platform",
    description: "Operator, measurement, analysis, and study tools",
    keywords: "study operator analysis measurement",
  },
  {
    href: "/imagina/live",
    label: "Live lab",
    description: "Technical preview of the adaptive loop",
    keywords: "demo telemetry policy",
  },
  {
    href: "/imagina/showcase",
    label: "Showcase",
    description: "Local demonstration dataset and reviewer checklist",
    keywords: "demo showcase reviewer",
  },
];

export function isNavLinkActive(pathname: string | null | undefined, href: string): boolean {
  if (!pathname) return false;
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function isLabRoute(pathname: string | null | undefined): boolean {
  if (!pathname) return false;
  return LAB_NAV.some((link) => isNavLinkActive(pathname, link.href)) || pathname.startsWith("/research/");
}
