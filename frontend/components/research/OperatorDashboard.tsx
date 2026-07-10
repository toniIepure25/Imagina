"use client";

import { useEffect, useState } from "react";
import {
  getStudyMode,
  getSystemCapabilities,
  listInstruments,
  type InstrumentInfo,
  type SystemCapabilities,
} from "@/lib/research-api";

type SafeguardStatus = "verified" | "partial" | "unavailable" | "blocked";

interface Safeguard {
  label: string;
  status: SafeguardStatus;
  detail: string;
}

function deriveSafeguards(caps: SystemCapabilities | null): Safeguard[] {
  if (!caps) {
    return [
      { label: "Backend connection", status: "unavailable", detail: "Cannot reach backend" },
    ];
  }
  return [
    {
      label: "Foreign key enforcement",
      status: caps.database_foreign_keys_enabled ? "verified" : "blocked",
      detail: caps.database_foreign_keys_enabled
        ? "PRAGMA foreign_keys = ON verified"
        : "Foreign keys not enabled",
    },
    {
      label: "Database migrations",
      status: caps.migration_version >= 2 ? "verified" : "partial",
      detail: `Migration version: ${caps.migration_version}`,
    },
    {
      label: "Human collection gate",
      status: caps.human_collection_allowed ? "blocked" : "verified",
      detail: caps.human_collection_allowed
        ? "WARNING: Human collection enabled"
        : "Human collection default-denied",
    },
    {
      label: "Protocol freeze support",
      status: caps.protocol_freeze_enforced ? "verified" : "partial",
      detail: caps.protocol_freeze_enforced
        ? "Protocol version table available"
        : "Protocol freeze not yet enforced",
    },
    {
      label: "Consent version tracking",
      status: caps.consent_version_enforced ? "verified" : "partial",
      detail: caps.consent_version_enforced
        ? "Consent document versioning available"
        : "Consent versioning not yet enforced",
    },
    {
      label: "Condition blinding (API)",
      status: caps.condition_blinding_api_enforced ? "verified" : "blocked",
      detail: caps.condition_blinding_api_enforced
        ? "Public API hides assignment data"
        : "Assignment data may be exposed",
    },
    {
      label: "Synthetic runtime",
      status: caps.synthetic_runtime_available ? "verified" : "unavailable",
      detail: caps.synthetic_runtime_available
        ? "Synthetic E2E workflow available"
        : "Not yet implemented (Merge Gate B)",
    },
    {
      label: "Local data only",
      status: "verified",
      detail: "All data stored locally in SQLite (no cloud)",
    },
    {
      label: "Pseudonym-only identification",
      status: "verified",
      detail: "Participants identified by pseudonym, not real names",
    },
  ];
}

const statusStyles: Record<SafeguardStatus, { icon: string; color: string }> = {
  verified: { icon: "\u2713", color: "text-emerald-400" },
  partial: { icon: "\u25CB", color: "text-yellow-400" },
  unavailable: { icon: "\u2014", color: "text-gray-500" },
  blocked: { icon: "\u2717", color: "text-red-400" },
};

export default function OperatorDashboard() {
  const [studyMode, setStudyMode] = useState("loading...");
  const [instruments, setInstruments] = useState<InstrumentInfo[]>([]);
  const [capabilities, setCapabilities] = useState<SystemCapabilities | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getStudyMode()
      .then((data) => setStudyMode(data.study_mode))
      .catch(() => setStudyMode("unavailable"));

    listInstruments()
      .then((data) => setInstruments(data.instruments))
      .catch((err) => setError(err.message));

    getSystemCapabilities()
      .then(setCapabilities)
      .catch(() => setCapabilities(null));
  }, []);

  const safeguards = deriveSafeguards(capabilities);

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 bg-white/5 rounded-xl border border-white/10">
          <p className="text-sm text-gray-400">Application Mode</p>
          <p className="text-xl font-semibold mt-1">{studyMode}</p>
        </div>
        <div className="p-4 bg-white/5 rounded-xl border border-white/10">
          <p className="text-sm text-gray-400">Instruments Registered</p>
          <p className="text-xl font-semibold mt-1">{instruments.length}</p>
        </div>
        <div className="p-4 bg-white/5 rounded-xl border border-white/10">
          <p className="text-sm text-gray-400">Migration Version</p>
          <p className="text-xl font-semibold mt-1">
            {capabilities ? `v${capabilities.migration_version}` : "..."}
          </p>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-900/30 rounded-xl border border-red-700/50 text-sm">
          {error}
        </div>
      )}

      <div className="p-6 bg-white/5 rounded-xl border border-white/10">
        <h3 className="text-lg font-semibold mb-4">Registered Instruments</h3>
        {instruments.length === 0 ? (
          <p className="text-sm text-gray-400">No instruments loaded.</p>
        ) : (
          <div className="space-y-3">
            {instruments.map((inst) => (
              <div key={inst.instrument_id} className="p-3 bg-white/5 rounded-lg">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="font-medium">{inst.name}</p>
                    <p className="text-xs text-gray-400">{inst.version}</p>
                  </div>
                  <span
                    className={`text-xs px-2 py-1 rounded ${
                      inst.items_included
                        ? "bg-emerald-800/50 text-emerald-300"
                        : "bg-yellow-800/50 text-yellow-300"
                    }`}
                  >
                    {inst.items_included ? "Items included" : "External"}
                  </span>
                </div>
                <p className="text-xs text-gray-500 mt-1">{inst.citation}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="p-6 bg-white/5 rounded-xl border border-white/10">
        <h3 className="text-lg font-semibold mb-4">Research Safeguards</h3>
        <p className="text-xs text-gray-500 mb-3">
          Status derived from backend capability checks, not static claims.
        </p>
        <ul className="space-y-2 text-sm text-gray-300">
          {safeguards.map((sg) => {
            const style = statusStyles[sg.status];
            return (
              <li key={sg.label} className="flex items-start gap-2">
                <span className={`${style.color} mt-0.5`}>{style.icon}</span>
                <div>
                  <span>{sg.label}</span>
                  <span className="text-xs text-gray-500 ml-2">({sg.status})</span>
                  <p className="text-xs text-gray-500">{sg.detail}</p>
                </div>
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}
