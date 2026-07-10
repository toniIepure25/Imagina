"use client";

import { useEffect, useState } from "react";

interface ConfidenceSummary {
  confirmed: number;
  strong_hypothesis: number;
  weak_hypothesis: number;
  unknown: number;
}

interface EventSemantics {
  stim_channels_found: boolean;
  subjects_with_stim: number;
  events_found: boolean;
  total_events: number | null;
  unique_event_codes_count: number;
  unique_event_codes: number[];
  semantic_mapping_resolved: boolean;
  mapping_confidence_summary: ConfidenceSummary;
  evidence_files_analyzed: number;
  confirmed_mappings_count: number;
  strong_hypothesis_count: number;
  weak_hypothesis_count: number;
  unresolved_codes_count: number;
  event_code_families: Record<string, { codes: number[]; count: number; description: string; structural_meaning: string; evidence_source: string; }>;
  beat_file_structure: Record<string, unknown>;
  condition_manifest_exists: boolean;
  draft_manifest_exists: boolean;
  blocked_reason: string;
  perception_imagery_evidence: Record<string, unknown>;
  event_sequence_available: boolean;
}

interface ConditionAnalysis {
  status: string;
  metadata_available: boolean;
  events_found: boolean;
  trigger_semantics_confirmed: boolean;
  semantic_mapping_resolved: boolean;
  beat_file_mapping_confirmed: boolean;
  draft_manifest_exists: boolean;
  condition_manifest_exists: boolean;
  blocked_reason: string;
  perception_imagery_map_confirmed: boolean;
  perception_codes: number[];
  imagery_codes: number[];
}

interface HardMetadataRecovery {
  xlsx_files_found: number;
  xlsx_files_parsed: number;
  matlab_files_found: number;
  matlab_files_parsed: number;
  excel_evidence_level: string;
  matlab_evidence_level: string;
  explicit_code_mappings_found: boolean;
  trigger_semantics_confirmed: boolean;
  perception_imagery_mapping_confirmed: boolean;
  stimulus_mapping_confirmed: boolean;
  production_manifest_exists: boolean;
  draft_manifest_exists: boolean;
}

interface StimtrackerValidation {
  available: boolean;
  overall_confidence: string;
  overall_score: number | null;
  empirical_mapping_validated: boolean;
  production_unlock_allowed: boolean;
  perception_codes: number[];
  imagery_codes: number[];
  baseline_codes: number[];
}

interface DashboardData {
  release_candidate: string;
  system_status: {
    real_eeg_imported: boolean;
    demo_status: string;
    scientific_validation_complete: boolean;
  };
  dataset: {
    name: string;
    subjects: number;
    channels: number | null;
    sampling_rate_hz: number | null;
    duration_seconds: number | null;
  };
  signal_quality: Record<string, number> | null;
  iqi_v2: {
    available: boolean;
    metric_version: string | null;
    mean: number | null;
    std: number | null;
    min: number | null;
    max: number | null;
    component_means: Record<string, number> | null;
    component_count: number;
  };
  openmiir_event_semantics: EventSemantics;
  condition_analysis: ConditionAnalysis;
  hard_metadata_recovery: HardMetadataRecovery;
  stimtracker_validation: StimtrackerValidation;
  condition_eval: {
    main_status: string;
    main_analysis_mode: string;
    experimental_available: boolean;
    experimental_status: string;
    experimental_not_for_scientific_claims: boolean | null;
    production_valid: boolean;
  };
  experimental_condition_analysis: {
    available: boolean;
    status: string;
    analysis_mode: string;
    not_for_scientific_claims: boolean | null;
    production_valid: boolean | null;
    n_subjects: number;
    n_conditions: number;
    fdr_significant_hits: number;
    top_effects: { comparison: string; feature: string; cohens_dz: number }[];
    figures_available: number;
    limitations_short: string[];
  };
  analysis_artifacts: Record<string, boolean>;
  limitations: string[];
  privacy_note: string;
  scientific_disclaimer: string;
}

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function Badge({ label, ok }: { label: string; ok: boolean }) {
  return (
    <span className={`rounded-full px-2 py-0.5 text-[10px] ${ok ? "bg-green-500/20 text-green-300" : "bg-yellow-500/20 text-yellow-300"}`}>
      {ok ? "\u2713" : "\u2190"} {label}
    </span>
  );
}

function CountBadge({ label, count, color }: { label: string; count: number; color: string }) {
  return (
    <span className={`rounded-full px-2 py-0.5 text-[9px] ${color}`}>
      {label}: {count}
    </span>
  );
}

export default function EEGValidationPage() {
  const [data, setData] = useState<DashboardData | null>(null);

  useEffect(() => {
    fetch(`${API}/api/research-dashboard/summary`)
      .then((r) => r.json())
      .then(setData);
  }, []);

  if (!data) return <div className="p-8 text-foreground/50">Loading research dashboard...</div>;

  const s = data.system_status;
  const d = data.dataset;
  const iq = data.iqi_v2;
  const es = data.openmiir_event_semantics;
  const ca = data.condition_analysis;
  const hr = data.hard_metadata_recovery;
  const sv = data.stimtracker_validation;
  const ce = data.condition_eval;
  const ea = data.experimental_condition_analysis;

  return (
    <main className="flex-1 mx-auto w-full max-w-6xl p-6 lg:p-10 space-y-6">
      {/* Hero */}
      <div className="glass panel-glow p-6 border-l-4 border-accent">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-[11px] uppercase tracking-[0.22em] text-accent-glow/70">Research Platform</div>
            <h1 className="mt-2 text-3xl font-bold glow-text">IMAGINA</h1>
            <p className="mt-1 text-sm text-foreground/60">{data.release_candidate}</p>
          </div>
          <div className="text-right space-y-1">
            <Badge label="Real EEG" ok={s.real_eeg_imported} />
            <div className="text-[10px] text-foreground/40">{s.demo_status}</div>
          </div>
        </div>
        <p className="mt-4 text-xs text-foreground/50">{data.scientific_disclaimer}</p>
      </div>

      {/* Dataset + IQI v2 + Condition + Evidence */}
      <div className="grid gap-4 md:grid-cols-4">
        <div className="glass panel-glow p-4">
          <div className="text-[10px] uppercase tracking-[0.16em] text-foreground/40">Dataset</div>
          <div className="mt-2 font-mono text-2xl font-bold text-accent-glow">{d.name}</div>
          <div className="mt-2 text-xs text-foreground/50 space-y-1">
            <div>Subjects: {d.subjects}</div>
            <div>Channels: {d.channels}</div>
            <div>Rate: {d.sampling_rate_hz} Hz</div>
          </div>
        </div>

        <div className="glass panel-glow p-4">
          <div className="text-[10px] uppercase tracking-[0.16em] text-foreground/40">IQI v2</div>
          <div className="mt-2 font-mono text-2xl font-bold text-accent-glow">
            {iq.available ? (iq.mean ?? 0).toFixed(3) : "N/A"}
          </div>
          <div className="mt-2 text-xs text-foreground/50 space-y-1">
            <div>Components: {iq.component_count}</div>
            <div>Range: [{iq.min?.toFixed(3)}, {iq.max?.toFixed(3)}]</div>
            <div>Metric: {iq.metric_version}</div>
          </div>
        </div>

        <div className="glass panel-glow p-4">
          <div className="text-[10px] uppercase tracking-[0.16em] text-foreground/40">Signal Quality</div>
          <div className="mt-2 font-mono text-2xl font-bold text-accent-glow">
            {data.signal_quality?.mean ? (data.signal_quality.mean * 100).toFixed(1) + "%" : "N/A"}
          </div>
          <div className="mt-2 text-xs text-foreground/50 space-y-1">
            <div>Min: {data.signal_quality?.min?.toFixed(3)}</div>
            <div>Max: {data.signal_quality?.max?.toFixed(3)}</div>
          </div>
        </div>

        <div className="glass panel-glow p-4">
          <div className="text-[10px] uppercase tracking-[0.16em] text-foreground/40">Condition Analysis</div>
          <div className="mt-2 font-mono text-lg font-bold text-amber-400">
            {ca.status.toUpperCase()}
          </div>
          <div className="mt-2 text-[10px] text-foreground/50 space-y-1">
            <div>Main: <span className={ce.production_valid ? "text-green-400" : "text-red-400"}>{ce.main_status}</span></div>
            <div>Exp: {ce.experimental_available ? <span className="text-purple-400">{ce.experimental_status}</span> : "N/A"}</div>
            <div>Prod: {ce.production_valid ? "Yes" : "No"}</div>
          </div>
        </div>
      </div>

      {/* Event Semantics Evidence */}
      <div className="glass panel-glow p-5 border-l-4 border-amber-500/50">
        <h2 className="text-lg font-semibold text-amber-300">OpenMIIR Event Semantics ΓÇö V3.9.3</h2>

        {/* Status row */}
        <div className="mt-3 grid gap-3 md:grid-cols-4 text-xs">
          <div>
            <div className="text-foreground/40 text-[9px] uppercase tracking-[0.1em] mb-2">Stim Channels</div>
            <div className="space-y-1">
              <Badge label="Stim Found" ok={es.stim_channels_found} />
              <Badge label="Events" ok={es.events_found} />
              <div className="text-foreground/50 font-mono">
                {es.subjects_with_stim}/10 subjects
              </div>
              <div className="text-foreground/50 font-mono">
                {es.total_events?.toLocaleString() || "?"} events
              </div>
            </div>
          </div>

          <div>
            <div className="text-foreground/40 text-[9px] uppercase tracking-[0.1em] mb-2">Evidence Files</div>
            <div className="space-y-1">
              <div className="text-foreground/50">
                <span className="text-accent-glow font-mono">{es.evidence_files_analyzed || "?"}</span> analyzed
              </div>
              <div className="text-foreground/50 font-mono">
                {es.unique_event_codes_count} unique codes
              </div>
            </div>
          </div>

          <div>
            <div className="text-foreground/40 text-[9px] uppercase tracking-[0.1em] mb-2">Confidence</div>
            <div className="space-y-1">
              <CountBadge label="Confirmed" count={es.confirmed_mappings_count} color="bg-green-500/20 text-green-300" />
              <CountBadge label="Strong" count={es.strong_hypothesis_count} color="bg-blue-500/20 text-blue-300" />
              <CountBadge label="Weak" count={es.weak_hypothesis_count} color="bg-amber-500/20 text-amber-300" />
              <CountBadge label="Unresolved" count={es.unresolved_codes_count} color="bg-red-500/20 text-red-300" />
            </div>
          </div>

          <div>
            <div className="text-foreground/40 text-[9px] uppercase tracking-[0.1em] mb-2">Manifests</div>
            <div className="space-y-1">
              <Badge label="Production" ok={es.condition_manifest_exists} />
              <Badge label="Draft" ok={es.draft_manifest_exists} />
              <Badge label="P/I Map" ok={ca.perception_imagery_map_confirmed} />
            </div>
          </div>
        </div>

        {/* Amber warning */}
        {!es.semantic_mapping_resolved && (
          <div className="mt-4 p-3 rounded-lg border border-amber-500/30 bg-amber-500/5">
            <p className="text-xs text-amber-400 leading-relaxed">
              Event markers are present, but semantic mapping to perception/imagery is not confirmed.
              Beat file naming confirms two-digit codes (11-44) map to stimulus├ùcue tracks.
              The 100-series vs 200-series distinction remains a structural hypothesis.
              IMAGINA therefore blocks scientific condition analysis.
            </p>
          </div>
        )}

        {/* Code Families Table */}
        <div className="mt-4">
          <div className="text-foreground/40 text-[9px] uppercase tracking-[0.1em] mb-2">
            Event Code Families
          </div>
          <div className="grid gap-2 md:grid-cols-2 text-[10px]">
            {Object.entries(es.event_code_families).map(([name, fam]) => (
              <div key={name} className="rounded-lg border border-surface-border bg-surface/30 p-2">
                <div className="text-foreground/60 font-mono text-[9px]">{name}</div>
                <div className="mt-1 text-accent-glow font-mono text-[9px] break-all">
                  {fam.codes.join(", ")}
                </div>
                <div className="mt-1 text-foreground/50 leading-relaxed">{fam.structural_meaning}</div>
                <div className="mt-1 text-foreground/40 text-[8px]">Source: {fam.evidence_source}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Beat file structure */}
        {Object.keys(es.beat_file_structure).length > 0 && (
          <div className="mt-4">
            <div className="text-foreground/40 text-[9px] uppercase tracking-[0.1em] mb-2">
              Beat File Structure (Confirmed)
            </div>
            <div className="text-[10px] text-foreground/50 bg-surface/30 p-2 rounded-lg font-mono">
              Pattern: {(es.beat_file_structure as Record<string, unknown>).pattern as string} |
              Stimuli: {String((es.beat_file_structure as Record<string, unknown>).stimuli)} |
              Cue types: {String((es.beat_file_structure as Record<string, unknown>).cue_types)}
            </div>
          </div>
        )}
      </div>

      {/* Hard Metadata Recovery */}
      <div className="glass panel-glow p-5 border-l-4 border-blue-500/50">
        <h2 className="text-lg font-semibold text-blue-300">Hard Metadata Recovery ΓÇö V3.9.4</h2>
        <div className="mt-3 grid gap-3 md:grid-cols-4 text-xs">
          <div>
            <div className="text-foreground/40 text-[9px] uppercase tracking-[0.1em] mb-2">Excel Metadata</div>
            <div className="space-y-1">
              <div className="text-foreground/50">
                <span className="text-blue-400 font-mono">{hr.xlsx_files_found}</span> found
              </div>
              <div className="text-foreground/50">
                <span className="text-blue-400 font-mono">{hr.xlsx_files_parsed}</span> parsed
              </div>
              <div className="text-foreground/50">Level: {hr.excel_evidence_level}</div>
            </div>
          </div>
          <div>
            <div className="text-foreground/40 text-[9px] uppercase tracking-[0.1em] mb-2">MATLAB Scripts</div>
            <div className="space-y-1">
              <div className="text-foreground/50">
                <span className="text-blue-400 font-mono">{hr.matlab_files_found}</span> found
              </div>
              <div className="text-foreground/50">
                <span className="text-blue-400 font-mono">{hr.matlab_files_parsed}</span> parsed
              </div>
              <div className="text-foreground/50">Level: {hr.matlab_evidence_level}</div>
            </div>
          </div>
          <div>
            <div className="text-foreground/40 text-[9px] uppercase tracking-[0.1em] mb-2">Trigger Semantics</div>
            <div className="space-y-1">
              <Badge label="MATLAB Triggers" ok={hr.trigger_semantics_confirmed} />
              <div className="text-[9px] text-foreground/50 leading-relaxed">
                1=perception, 2=cued imagery, 3=uncued imagery, 4=noise
              </div>
            </div>
          </div>
          <div>
            <div className="text-foreground/40 text-[9px] uppercase tracking-[0.1em] mb-2">Explicit Mappings</div>
            <div className="space-y-1">
              <Badge label="Code Maps" ok={hr.explicit_code_mappings_found} />
              <Badge label="P/I Confirmed" ok={hr.perception_imagery_mapping_confirmed} />
              <Badge label="Production Manifest" ok={hr.production_manifest_exists} />
            </div>
          </div>
        </div>
        {hr.trigger_semantics_confirmed && !hr.perception_imagery_mapping_confirmed && (
          <div className="mt-4 p-3 rounded-lg border border-blue-500/30 bg-blue-500/5">
            <p className="text-xs text-blue-400 leading-relaxed">
              MATLAB code confirms trigger semantics: 1=perception, 2=cued_imagery, 3=uncued_imagery, 4=noise.
              Two-digit stim codes ({'{'}stimulus{'_'}group{'}{'}trigger{'_'}type{'}'}) map to conditions via
              strong hypothesis. Production condition analysis is unlocked only after
              explicit StimTracker encoding is confirmed.
            </p>
          </div>
        )}
      </div>

      {/* StimTracker Encoding Validation */}
      <div className="glass panel-glow p-5 border-l-4 border-purple-500/50">
        <h2 className="text-lg font-semibold text-purple-300">StimTracker Encoding Validation ΓÇö V3.9.5</h2>
        <div className="mt-3 grid gap-3 md:grid-cols-4 text-xs">
          <div>
            <div className="text-foreground/40 text-[9px] uppercase tracking-[0.1em] mb-2">Validation</div>
            <div className="space-y-1">
              <div className="text-foreground/50">Score: <span className="text-purple-400 font-mono">{sv.overall_score?.toFixed(3) || "N/A"}</span></div>
              <div className="text-foreground/50">Confidence: <span className="text-purple-400 font-mono">{sv.overall_confidence}</span></div>
              <Badge label="Empirical" ok={sv.empirical_mapping_validated} />
            </div>
          </div>
          <div>
            <div className="text-foreground/40 text-[9px] uppercase tracking-[0.1em] mb-2">Production</div>
            <div className="space-y-1">
              <Badge label="Prod Unlocked" ok={sv.production_unlock_allowed} />
              <div className="text-[9px] text-foreground/50">Documentation required</div>
            </div>
          </div>
          <div>
            <div className="text-foreground/40 text-[9px] uppercase tracking-[0.1em] mb-2">Perception</div>
            <div className="font-mono text-purple-400 text-[9px]">{sv.perception_codes.join(", ")}</div>
          </div>
          <div>
            <div className="text-foreground/40 text-[9px] uppercase tracking-[0.1em] mb-2">Imagery</div>
            <div className="font-mono text-purple-400 text-[9px]">{sv.imagery_codes.join(", ")}</div>
          </div>
        </div>
        <div className="mt-4 p-3 rounded-lg border border-purple-500/30 bg-purple-500/5">
          <p className="text-xs text-purple-400 leading-relaxed">
            Empirical validation is not documentation. Production condition analysis requires confirmed
            StimTracker encoding documentation. Use --allow-empirical-hypothesis for experimental analysis only.
          </p>
        </div>
      </div>

      {/* Experimental Condition EEG Analysis */}
      <div className="glass panel-glow p-5 border-l-4 border-pink-500/50">
        <h2 className="text-lg font-semibold text-pink-300">Experimental Condition EEG Analysis ΓÇö V3.9.6</h2>
        <div className="mt-3 grid gap-3 md:grid-cols-4 text-xs">
          <div>
            <div className="text-foreground/40 text-[9px] uppercase tracking-[0.1em] mb-2">Status</div>
            <div className="space-y-1">
              <Badge label="Available" ok={ea.available} />
              <div className="text-foreground/50">Mode: <span className="text-pink-400">{ea.analysis_mode}</span></div>
              <div className="text-foreground/50">Prod valid: {ea.production_valid ? "Yes" : <span className="text-red-400">No</span>}</div>
            </div>
          </div>
          <div>
            <div className="text-foreground/40 text-[9px] uppercase tracking-[0.1em] mb-2">Subjects</div>
            <div className="space-y-1">
              <div className="text-foreground/50">N: <span className="text-pink-400 font-mono">{ea.n_subjects || "?"}</span></div>
              <div className="text-foreground/50">Conditions: <span className="text-pink-400 font-mono">{ea.n_conditions || "?"}</span></div>
              <div className="text-foreground/50">FDR hits: <span className="text-pink-400 font-mono">{ea.fdr_significant_hits || 0}</span></div>
            </div>
          </div>
          <div>
            <div className="text-foreground/40 text-[9px] uppercase tracking-[0.1em] mb-2">Top Effects</div>
            <div className="space-y-1 max-h-24 overflow-y-auto">
              {ea.top_effects?.slice(0, 4).map((e, i) => (
                <div key={i} className="text-[9px] text-foreground/50 font-mono">
                  {e.comparison}/{e.feature}: {e.cohens_dz?.toFixed(2)}
                </div>
              )) || <div className="text-foreground/50">N/A</div>}
            </div>
          </div>
          <div>
            <div className="text-foreground/40 text-[9px] uppercase tracking-[0.1em] mb-2">Figures</div>
            <div className="space-y-1">
              <div className="text-foreground/50 font-mono">{ea.figures_available || 0} generated</div>
              <Badge label="Sci claims" ok={false} />
            </div>
          </div>
        </div>
        <div className="mt-4 p-3 rounded-lg border border-pink-500/30 bg-pink-500/5">
          <p className="text-xs text-pink-400 leading-relaxed">
            Experimental hypothesis only ΓÇö not valid for scientific claims. StimTracker encoding is
            empirically validated but not confirmed by documentation. All findings require independent replication.
          </p>
        </div>
      </div>

      {/* Analysis Modules */}
      <div className="glass panel-glow p-5">
        <h2 className="text-lg font-semibold text-accent-glow">Analysis Modules</h2>
        <div className="mt-3 grid gap-2 md:grid-cols-4 text-xs">
          {Object.entries(data.analysis_artifacts).map(([key, ok]) => (
            <div key={key} className="rounded-lg border border-surface-border bg-surface/30 p-2">
              <Badge label={key.replace(/_/g, " ")} ok={ok} />
            </div>
          ))}
        </div>
      </div>

      {/* IQI v2 Components */}
      {iq.component_means && (
        <div className="glass panel-glow p-5">
          <h2 className="text-lg font-semibold text-accent-glow">IQI v2 Components</h2>
          <div className="mt-3 grid gap-2 md:grid-cols-4 text-xs">
            {Object.entries(iq.component_means).map(([name, val]) => (
              <div key={name} className="rounded-lg border border-surface-border bg-surface/30 p-2">
                <div className="text-foreground/40 text-[9px] uppercase tracking-[0.1em]">
                  {name.replace(/([A-Z])/g, " $1").trim()}
                </div>
                <div className="mt-1 font-mono text-accent-glow">{val.toFixed(3)}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Limitations */}
      <div className="glass panel-glow p-5 border-l-4 border-yellow-500/50">
        <h2 className="text-lg font-semibold">Scientific Limitations</h2>
        <ul className="mt-3 space-y-1 text-xs text-foreground/55">
          {data.limitations.map((lim, i) => (
            <li key={i}>- {lim}</li>
          ))}
        </ul>
        <p className="mt-4 text-[10px] text-foreground/35">{data.privacy_note}</p>
      </div>
    </main>
  );
}