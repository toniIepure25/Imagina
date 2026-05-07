export interface FeedbackAction {
  session_id: string;
  timestamp: string;
  window_index: number;
  action_id: string;
  scene_clarity: number;
  blur: number;
  wall_distortion: number;
  light_stability: number;
  texture_detail: number;
  particle_stability: number;
  door_complexity: number;
  fog_density: number;
  color_saturation: number;
  breathing_cue_strength: number;
  prompt_text: string;
  reason: string;
}

export interface FeatureVector {
  session_id: string;
  timestamp: string;
  window_index: number;
  theta_power: number;
  alpha_power: number;
  beta_power: number;
  theta_beta_ratio: number;
  alpha_stability: number;
  signal_quality: number;
  simulated_imagery_strength: number;
  behavioral_stability: number;
  reaction_time_ms: number | null;
}

export interface StateEstimate {
  session_id: string;
  timestamp: string;
  window_index: number;
  attention_stability: number;
  relaxation: number;
  imagery_engagement: number;
  behavioral_consistency: number;
  fatigue: number;
  uncertainty: number;
  confidence: number;
}

export interface PIDEstimate {
  session_id: string;
  timestamp: string;
  window_index: number;
  pid: number;
  neural_proxy_distance: number;
  behavioral_distance: number;
  uncertainty_component: number;
  interpretation: string;
}

export interface IQIEstimate {
  session_id: string;
  timestamp: string;
  window_index: number;
  iqi: number;
  stability_component: number;
  engagement_component: number;
  relaxation_component: number;
  confidence: number;
}

export interface CurriculumState {
  session_id: string;
  timestamp: string;
  current_level: number;
  level_name: string;
  consecutive_successes: number;
  consecutive_failures: number;
  difficulty: number;
  reason: string;
}

export interface SafetyEvent {
  session_id: string;
  timestamp: string;
  severity: "info" | "warning" | "stop";
  event_type: string;
  message: string;
  recommended_action: string;
}

export interface SessionSummary {
  session_id: string;
  duration_seconds: number;
  average_pid: number;
  best_pid: number;
  average_iqi: number;
  best_iqi: number;
  max_level_reached: number;
  best_stability_streak_seconds: number;
  fatigue_peak: number;
  safety_events_count: number;
  recommendation: string;
  generated_at: string;
}

export interface ReportTimelineEvent {
  event_type: string;
  timestamp: string;
  payload: Record<string, unknown>;
}

export interface SessionReport {
  disclaimer: string;
  session_id: string;
  metadata?: {
    user_id: string;
    display_name: string | null;
    mode: string;
    task_id: string;
    signal_provider_id: string;
    scenario: string | null;
    experiment_run_id: string | null;
    status: string;
    created_at: string;
    started_at: string | null;
    ended_at: string | null;
  };
  calibration?: CalibrationProfile | null;
  experiment?: ExperimentProgress | null;
  summary: SessionSummary;
  analysis?: {
    iqi_slope: number;
    pid_slope: number;
    uncertainty_peak: number;
    level_advances: number;
    level_regressions: number;
    self_report_count: number;
  };
  timeline: ReportTimelineEvent[];
  exports?: Record<string, string>;
  event_count: number;
}

export interface WSMessage {
  type: string;
  timestamp: string;
  payload: Record<string, unknown>;
}

export interface Session {
  session_id: string;
  user_id: string;
  display_name: string | null;
  mode: "simulated" | "replay" | "manual";
  status: string;
  task_id: string;
  signal_provider_id: string;
  scenario: string | null;
  experiment_run_id: string | null;
  created_at: string;
  started_at: string | null;
  ended_at: string | null;
  safety_disclaimer_acknowledged: boolean;
}

export interface ImageryProfile {
  user_id: string;
  display_name: string;
  total_sessions: number;
  total_minutes: number;
  max_level_reached: number;
  average_iqi: number;
  best_iqi: number;
  average_pid: number;
  best_pid: number;
  fatigue_sensitivity: number;
  preferred_task_type: string;
  preferred_feedback_style: string;
  optimal_difficulty_estimate: number;
  progress_history_summary: Record<string, unknown>[];
  processed_session_ids?: string[];
}

export interface CalibrationProfile {
  calibration_id: string;
  session_id: string;
  user_id: string | null;
  duration_seconds: number;
  mode: string;
  baseline_focus: number;
  baseline_relaxation: number;
  baseline_vividness: number;
  baseline_fatigue: number;
  baseline_signal_quality: number;
  calibration_quality_score: number;
  warnings: string[];
  normalization_params: Record<string, unknown>;
  notes: string | null;
}

export interface SignalProviderInfo {
  provider_id: string;
  provider_type: string;
  name?: string;
  description?: string;
  health: {
    status: string;
    message?: string;
    available?: boolean;
  };
}

export interface ExperimentProtocol {
  protocol_id: string;
  name: string;
  description: string;
  condition: string;
  task_sequence: string[];
  duration_minutes: number;
  feedback_mode: string;
  curriculum_mode: string;
  catch_trial_rate: number;
  metrics_to_collect: string[];
}

export interface ExperimentRun {
  run_id: string;
  protocol_id: string;
  participant_label: string;
  status: string;
  session_ids: string[];
  completed_session_ids: string[];
  planned_sessions: Record<string, unknown>[];
  current_step: number;
  condition: string | null;
  catch_trials: number[];
  started_at: string;
  completed_at?: string | null;
}

export interface ExperimentProgress {
  run: ExperimentRun;
  protocol: ExperimentProtocol | null;
  planned_count: number;
  completed_count: number;
  current_step: number;
  next_step: Record<string, unknown> | null;
  percent_complete: number;
}
