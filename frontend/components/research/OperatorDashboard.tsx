"use client";

import { useEffect, useState } from "react";
import { getStudyMode, listInstruments, type InstrumentInfo } from "@/lib/research-api";

export default function OperatorDashboard() {
  const [studyMode, setStudyMode] = useState("loading...");
  const [instruments, setInstruments] = useState<InstrumentInfo[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getStudyMode()
      .then((data) => setStudyMode(data.study_mode))
      .catch(() => setStudyMode("unavailable"));

    listInstruments()
      .then((data) => setInstruments(data.instruments))
      .catch((err) => setError(err.message));
  }, []);

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 bg-white/5 rounded-xl border border-white/10">
          <p className="text-sm text-gray-400">Study Mode</p>
          <p className="text-xl font-semibold mt-1">{studyMode}</p>
        </div>
        <div className="p-4 bg-white/5 rounded-xl border border-white/10">
          <p className="text-sm text-gray-400">Instruments Registered</p>
          <p className="text-xl font-semibold mt-1">{instruments.length}</p>
        </div>
        <div className="p-4 bg-white/5 rounded-xl border border-white/10">
          <p className="text-sm text-gray-400">System Version</p>
          <p className="text-xl font-semibold mt-1">0.5.0-research</p>
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
                  <span className={`text-xs px-2 py-1 rounded ${inst.items_included ? "bg-emerald-800/50 text-emerald-300" : "bg-yellow-800/50 text-yellow-300"}`}>
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
        <ul className="space-y-2 text-sm text-gray-300">
          <li className="flex items-center gap-2">
            <span className="text-emerald-400">&#10003;</span>
            Consent required before data collection
          </li>
          <li className="flex items-center gap-2">
            <span className="text-emerald-400">&#10003;</span>
            Participants identified by pseudonym only
          </li>
          <li className="flex items-center gap-2">
            <span className="text-emerald-400">&#10003;</span>
            All data stored locally (no cloud)
          </li>
          <li className="flex items-center gap-2">
            <span className="text-emerald-400">&#10003;</span>
            Condition assignment blinded from participant
          </li>
          <li className="flex items-center gap-2">
            <span className="text-emerald-400">&#10003;</span>
            Safety monitor active (fatigue, overeffort, time limits)
          </li>
          <li className="flex items-center gap-2">
            <span className="text-emerald-400">&#10003;</span>
            Withdrawal mechanism available
          </li>
        </ul>
      </div>
    </div>
  );
}
