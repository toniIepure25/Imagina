"use client";

import { useEffect, useState } from "react";
import Panel from "@/components/platform/Panel";
import {
  getStudyMode,
  getSystemCapabilities,
  listInstruments,
  type InstrumentInfo,
  type SystemCapabilities,
} from "@/lib/research-api";

type SafeguardStatus = "verified" | "partial" | "unavailable" | "blocked" | "policy_only";

interface Safeguard {
  label: string;
  status: SafeguardStatus;
  detail: string;
}

function capStatusToSafeguard(capStatus: string): SafeguardStatus {
  if (capStatus === "verified_runtime") return "verified";
  if (capStatus === "implemented") return "partial";
  if (capStatus === "partial") return "partial";
  if (capStatus === "blocked") return "blocked";
  if (capStatus === "policy_only") return "policy_only";
  return "unavailable";
}

function deriveSafeguards(caps: SystemCapabilities | null): Safeguard[] {
  if (!caps) {
    return [{ label: "Backend connection", status: "unavailable", detail: "Cannot reach backend" }];
  }
  return [
    {
      label: "Foreign key enforcement",
      status: caps.database_foreign_keys_enabled ? "verified" : "blocked",
      detail: caps.database_foreign_keys_enabled ? "PRAGMA foreign_keys = ON verified" : "Foreign keys not enabled",
    },
    {
      label: "Database migrations",
      status: caps.migration_version >= 2 ? "partial" : "unavailable",
      detail: `Migration version: v${caps.migration_version}`,
    },
    {
      label: "Human collection gate",
      status: caps.human_collection_allowed ? "blocked" : "verified",
      detail: caps.human_collection_allowed ? "WARNING: Human collection enabled" : "Human collection default-denied",
    },
    {
      label: "Protocol freeze",
      status: capStatusToSafeguard(caps.protocol_freeze?.status),
      detail: caps.protocol_freeze?.detail ?? "Unknown",
    },
    {
      label: "Consent version tracking",
      status: capStatusToSafeguard(caps.consent_tracking?.status),
      detail: caps.consent_tracking?.detail ?? "Unknown",
    },
    {
      label: "Condition blinding (API)",
      status: capStatusToSafeguard(caps.condition_blinding?.status),
      detail: caps.condition_blinding?.detail ?? "Unknown",
    },
    {
      label: "Sequence allocation",
      status: capStatusToSafeguard(caps.sequence_allocation?.status),
      detail: caps.sequence_allocation?.detail ?? "Unknown",
    },
    {
      label: "Synthetic runtime",
      status: capStatusToSafeguard(caps.synthetic_runtime?.status),
      detail: caps.synthetic_runtime?.detail ?? "Not yet available",
    },
    {
      label: "Local data only",
      status: "policy_only",
      detail: "Architectural design constraint — not runtime-verified",
    },
    {
      label: "Pseudonym-only identification",
      status: "policy_only",
      detail: "Architectural design constraint — not runtime-verified",
    },
  ];
}

const STATUS_STYLES: Record<SafeguardStatus, { icon: string; color: string }> = {
  verified: { icon: "\u2713", color: "text-signal" },
  partial: { icon: "\u25CB", color: "text-lock" },
  unavailable: { icon: "\u2014", color: "text-foreground/35" },
  blocked: { icon: "\u2717", color: "text-danger" },
  policy_only: { icon: "\u25A0", color: "text-accent-glow" },
};

export default function OperatorDashboard() {
  const [studyMode, setStudyMode] = useState("loading…");
  const [instruments, setInstruments] = useState<InstrumentInfo[]>([]);
  const [capabilities, setCapabilities] = useState<SystemCapabilities | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getStudyMode()
      .then((data) => setStudyMode(data.study_mode))
      .catch(() => setStudyMode("unavailable"));

    listInstruments()
      .then((data) => setInstruments(data.instruments))
      .catch((caught: unknown) =>
        setError(caught instanceof Error ? caught.message : "Instrument registry unavailable."),
      );

    getSystemCapabilities()
      .then(setCapabilities)
      .catch(() => setCapabilities(null));
  }, []);

  const safeguards = deriveSafeguards(capabilities);

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {[
          ["Application mode", studyMode],
          ["Instruments registered", String(instruments.length)],
          ["Migration version", capabilities ? `v${capabilities.migration_version}` : "…"],
        ].map(([label, value]) => (
          <div key={label} className="rounded-lg border border-surface-border bg-white/[0.025] p-4">
            <p className="mono-label text-foreground/40">{label}</p>
            <p className="mt-1 font-mono text-xl text-foreground/80">{value}</p>
          </div>
        ))}
      </div>

      {error ? (
        <p role="alert" className="rounded-lg border border-danger/30 bg-danger/[0.05] p-3 text-sm text-danger">
          {error}
        </p>
      ) : null}

      <Panel className="p-5">
        <h2 className="text-base font-semibold">Registered instruments</h2>
        {instruments.length === 0 ? (
          <p className="mt-2 text-sm text-foreground/45">No instruments loaded.</p>
        ) : (
          <div className="mt-3 space-y-2">
            {instruments.map((instrument) => (
              <div key={instrument.instrument_id} className="rounded-lg border border-surface-border bg-white/[0.02] p-3">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <p className="text-sm font-medium text-foreground/80">{instrument.name}</p>
                    <p className="mt-0.5 font-mono text-[11px] text-foreground/35">{instrument.version}</p>
                  </div>
                  <span
                    className={`rounded-full border px-2 py-0.5 text-[11px] ${
                      instrument.items_included
                        ? "border-signal/30 bg-signal/[0.07] text-signal"
                        : "border-lock/30 bg-lock/[0.07] text-lock"
                    }`}
                  >
                    {instrument.items_included ? "Items included" : "External"}
                  </span>
                </div>
                <p className="mt-1.5 text-[11px] leading-5 text-foreground/40">{instrument.citation}</p>
              </div>
            ))}
          </div>
        )}
      </Panel>

      <Panel className="p-5">
        <h2 className="text-base font-semibold">Research safeguards</h2>
        <p className="mt-1 text-[11px] leading-5 text-foreground/40">
          Status derived from local capability checks. Items marked “policy” are architectural constraints, not
          runtime-verified properties.
        </p>
        <ul className="mt-3 space-y-2 text-sm">
          {safeguards.map((safeguard) => {
            const style = STATUS_STYLES[safeguard.status];
            return (
              <li key={safeguard.label} className="flex items-start gap-2">
                <span className={`${style.color} mt-0.5 font-mono`} aria-hidden="true">
                  {style.icon}
                </span>
                <div>
                  <span className="text-foreground/70">{safeguard.label}</span>
                  <span className="ml-2 font-mono text-[11px] text-foreground/35">({safeguard.status})</span>
                  <p className="text-[11px] leading-5 text-foreground/40">{safeguard.detail}</p>
                </div>
              </li>
            );
          })}
        </ul>
      </Panel>
    </div>
  );
}
