import { apiFetch } from "./api";

export interface Study {
  study_id: string;
  title: string;
  protocol_version: string;
  conditions: string[];
  description: string;
  ethics_status: string;
  ethics_reference: string;
  created_at: string;
  status: string;
}

export interface Participant {
  participant_id: string;
  pseudonym: string;
  study_id: string;
  eligibility_confirmed: boolean;
  condition_sequence: string[];
  sessions_completed: number;
  created_at: string;
  randomization_seed: number;
}

export interface ConsentRecord {
  consent_id: string;
  participant_id: string;
  study_id: string;
  consent_version: string;
  consented_at: string;
  withdrawn: boolean;
  withdrawn_at: string | null;
}

export interface InstrumentInfo {
  instrument_id: string;
  name: string;
  version: string;
  citation: string;
  license_status: string;
  scoring_direction: string;
  items_included: boolean;
  acquisition_instructions: string;
}

export interface CapabilityDetail {
  schema_available: boolean;
  service_available: boolean;
  runtime_gate_active: boolean;
  status: string;
  detail: string;
}

export interface SystemCapabilities {
  study_mode: string;
  database_foreign_keys_enabled: boolean;
  migration_version: number;
  human_collection_allowed: boolean;
  synthetic_runtime_available: boolean;
  protocol_freeze: CapabilityDetail;
  consent_tracking: CapabilityDetail;
  condition_blinding: CapabilityDetail;
  sequence_allocation: CapabilityDetail;
  synthetic_runtime: CapabilityDetail;
  checked_at: string;
}

export async function getStudyMode(): Promise<{ study_mode: string }> {
  return apiFetch("/api/research-protocol/mode");
}

export async function listStudies(): Promise<{ studies: Study[] }> {
  return apiFetch("/api/research-protocol/studies");
}

export async function getStudy(studyId: string): Promise<Study> {
  return apiFetch(`/api/research-protocol/studies/${studyId}`);
}

export async function listParticipants(studyId: string): Promise<{ participants: Participant[] }> {
  return apiFetch(`/api/research-protocol/studies/${studyId}/participants`);
}

export async function checkConsent(participantId: string, studyId: string): Promise<{ has_valid_consent: boolean }> {
  return apiFetch(`/api/research-protocol/consent/${participantId}/${studyId}`);
}

export async function recordConsent(data: {
  participant_id: string;
  study_id: string;
  consent_version: string;
}): Promise<ConsentRecord> {
  return apiFetch("/api/research-protocol/consent", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function listInstruments(): Promise<{ instruments: InstrumentInfo[] }> {
  return apiFetch("/api/research-protocol/instruments");
}

export async function getSystemCapabilities(): Promise<SystemCapabilities> {
  return apiFetch("/api/research-protocol/capabilities");
}

export async function getConditionAssignment(
  studyId: string,
  participantId: string,
  sessionIndex: number
): Promise<{ condition: string; session_index: number }> {
  return apiFetch(`/api/research-protocol/studies/${studyId}/condition/${participantId}/${sessionIndex}`);
}
