"use client";

import { useEffect, useState } from "react";

interface DatasetInfo {
  dataset_id: string;
  name: string;
  source?: string;
  status: string;
  format?: string;
  real_signal: boolean;
  download_supported: boolean;
  requires_manual_download: boolean;
  estimated_size_gb?: number | null;
  notes?: string;
}

interface FinalDemoStatus {
  release_candidate: string;
  demo_status: string;
  real_eeg_imported: boolean;
  real_scientific_validation_complete: boolean;
  real_dataset?: string | null;
  real_file_count?: number;
  real_sampling_rate_hz?: number;
  real_channel_count?: number;
  real_signal_quality_mean?: number;
  real_quality_warnings?: string[];
  next_required_action?: string;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function DatasetReadinessPanel() {
  const [catalog, setCatalog] = useState<DatasetInfo[]>([]);
  const [status, setStatus] = useState<FinalDemoStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_URL}/api/datasets/catalog`)
      .then((r) => r.json())
      .then(setCatalog)
      .catch(() => setError("Backend unavailable"));
    fetch(`${API_URL}/api/datasets/final-demo-status`)
      .then((r) => r.json())
      .then(setStatus)
      .catch(() => {});
  }, []);

  return (
    <div className="glass panel-glow p-5 space-y-4">
      {status && (
        <div className="rounded-lg border border-accent/30 bg-accent/10 p-4">
          <div className="flex items-center justify-between">
            <span className="text-lg font-bold text-accent-glow">
              {status.release_candidate}
            </span>
            <span className="rounded-full bg-green-500/20 px-3 py-1 text-xs text-green-300">
              {status.demo_status}
            </span>
          </div>
          <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-foreground/60">
            <div>Real EEG imported: {status.real_eeg_imported ? "\u2713 Yes" : "\u2717 No"}</div>
            <div>Scientific validation: {status.real_scientific_validation_complete ? "Complete" : "Not complete"}</div>
            {status.real_dataset && <div>Dataset: {status.real_dataset}</div>}
            {status.real_file_count != null && <div>Files: {status.real_file_count}</div>}
            {status.real_sampling_rate_hz != null && <div>Rate: {status.real_sampling_rate_hz} Hz</div>}
            {status.real_channel_count != null && <div>Channels: {status.real_channel_count}</div>}
            {status.real_signal_quality_mean != null && (
              <div>Signal quality: {(status.real_signal_quality_mean * 100).toFixed(1)}%</div>
            )}
          </div>
        </div>
      )}
      {status?.next_required_action && (
        <div className="text-xs text-foreground/50">{status.next_required_action}</div>
      )}
      <div className="rounded-lg border border-yellow-400/20 bg-yellow-400/5 p-3 text-[11px] text-yellow-100/70">
        Experimental proxy features only. Not clinical EEG analysis. No raw EEG samples are exposed.
      </div>
    </div>
  );
}
