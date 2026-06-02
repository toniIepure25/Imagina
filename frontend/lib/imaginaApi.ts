"use client";

const API = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export async function health() {
  const r = await fetch(`${API}/api/imagina/health`);
  return r.json();
}

export async function startSession(payload: { demo_mode?: boolean; demo_profile?: string; user_id?: string }) {
  const r = await fetch(`${API}/api/imagina/session/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return r.json();
}

export async function startTask(sessionId: string, taskId: string) {
  const r = await fetch(`${API}/api/imagina/session/${sessionId}/task/start?task_id=${taskId}`, {
    method: "POST",
  });
  return r.json();
}

export async function submitSelfReport(sessionId: string, payload: {
  vividness: number; stability: number; effort: number; fatigue: number; comfort: number; task_id?: string;
}) {
  const r = await fetch(`${API}/api/imagina/session/${sessionId}/self-report`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return r.json();
}

export async function runStep(sessionId: string) {
  const r = await fetch(`${API}/api/imagina/session/${sessionId}/step`, { method: "POST" });
  return r.json();
}

export async function getSummary(sessionId: string) {
  const r = await fetch(`${API}/api/imagina/session/${sessionId}/summary`);
  return r.json();
}

export async function getEvents(sessionId: string) {
  const r = await fetch(`${API}/api/imagina/session/${sessionId}/events`);
  return r.json();
}

export async function getProfile(userId: string) {
  const r = await fetch(`${API}/api/imagina/profile/${userId}`);
  return r.json();
}

export async function updateProfileFromSession(userId: string, sessionId: string) {
  const r = await fetch(`${API}/api/imagina/profile/${userId}/update-from-session/${sessionId}`, { method: "POST" });
  return r.json();
}

export async function resetProfile(userId: string) {
  const r = await fetch(`${API}/api/imagina/profile/${userId}/reset`, { method: "POST" });
  return r.json();
}

export async function getSessionAnalytics(sessionId: string) {
  const r = await fetch(`${API}/api/imagina/session/${sessionId}/analytics`);
  return r.json();
}

export async function getRecommendations(userId: string) {
  const r = await fetch(`${API}/api/imagina/recommendations/${userId}`);
  return r.json();
}

// ─── Protocol Engine ────────────────────────

export async function getProtocolTemplates() {
  const r = await fetch(`${API}/api/imagina/protocols/templates`);
  return r.json();
}

export async function createProtocol(userId: string, templateName: string) {
  const r = await fetch(`${API}/api/imagina/protocols/${userId}/create?template_name=${templateName}`, { method: "POST" });
  return r.json();
}

export async function listProtocols(userId: string) {
  const r = await fetch(`${API}/api/imagina/protocols/${userId}`);
  return r.json();
}

export async function startProtocolRun(userId: string, protocolId: string) {
  const r = await fetch(`${API}/api/imagina/protocol-runs/${userId}/start/${protocolId}`, { method: "POST" });
  return r.json();
}

export async function attachSessionToRun(runId: string, sessionId: string) {
  const r = await fetch(`${API}/api/imagina/protocol-runs/${runId}/attach-session/${sessionId}`, { method: "POST" });
  return r.json();
}

export async function getNextProtocolStep(runId: string) {
  const r = await fetch(`${API}/api/imagina/protocol-runs/${runId}/next-step`);
  return r.json();
}

export async function completeProtocolRun(runId: string) {
  const r = await fetch(`${API}/api/imagina/protocol-runs/${runId}/complete`, { method: "POST" });
  return r.json();
}

export async function getProtocolAnalysis(runId: string) {
  const r = await fetch(`${API}/api/imagina/protocol-runs/${runId}/analysis`);
  return r.json();
}

// ─── Experiment Designer ────────────────────

export async function getExperimentTemplates() {
  const r = await fetch(`${API}/api/imagina/experiment-designs/templates`);
  return r.json();
}

export async function createExperimentDesign(userId: string, templateId: string) {
  const r = await fetch(`${API}/api/imagina/experiment-designs/${userId}/create?template_id=${templateId}`, { method: "POST" });
  return r.json();
}

export async function listExperimentDesigns(userId: string) {
  const r = await fetch(`${API}/api/imagina/experiment-designs/${userId}`);
  return r.json();
}

export async function validateExperimentDesign(userId: string, designId: string) {
  const r = await fetch(`${API}/api/imagina/experiment-designs/${userId}/${designId}/validate`, { method: "POST" });
  return r.json();
}

export async function compileExperimentDesign(userId: string, designId: string) {
  const r = await fetch(`${API}/api/imagina/experiment-designs/${userId}/${designId}/compile`, { method: "POST" });
  return r.json();
}

export async function createProtocolFromDesign(userId: string, designId: string) {
  const r = await fetch(`${API}/api/imagina/protocols/${userId}/create-from-design/${designId}`, { method: "POST" });
  return r.json();
}

// ─── Personal Intelligence ────────────────────

export async function getPersonalProfile() {
  const r = await fetch(`${API}/api/imagina/personal-profile`);
  return r.json();
}

export async function rebuildPersonalProfile() {
  const r = await fetch(`${API}/api/imagina/personal-profile/rebuild`, { method: "POST" });
  return r.json();
}

export async function getImageryGaps() {
  const r = await fetch(`${API}/api/imagina/imagery-gaps`);
  return r.json();
}

export async function getNextRecommendation() {
  const r = await fetch(`${API}/api/imagina/recommendation/next`);
  return r.json();
}

export async function createRecommendedDesign() {
  const r = await fetch(`${API}/api/imagina/recommendation/create-design`, { method: "POST" });
  return r.json();
}

export async function getPersonalReport() {
  const r = await fetch(`${API}/api/imagina/personal-report`);
  return r.json();
}

// ─── V14 Adaptive Training Loop ────────────────────

export async function getAdaptivePlan(userId: string) {
  const r = await fetch(`${API}/api/imagina/adaptive/plan/${userId}`);
  if (!r.ok) throw new Error("No plan found");
  return r.json();
}

export async function generateAdaptivePlan(userId: string) {
  const r = await fetch(`${API}/api/imagina/adaptive/plan/${userId}/generate`, { method: "POST" });
  if (!r.ok) throw new Error("Cannot generate plan");
  return r.json();
}

export async function listAdaptivePlans(userId: string) {
  const r = await fetch(`${API}/api/imagina/adaptive/plans/${userId}`);
  return r.json();
}

export async function getPidImprovement(userId: string) {
  const r = await fetch(`${API}/api/imagina/adaptive/improvement/${userId}`);
  return r.json();
}

export async function getTrainingResponse(userId: string) {
  const r = await fetch(`${API}/api/imagina/adaptive/training-response/${userId}`);
  return r.json();
}

export async function regenerateAdaptivePlan(userId: string, payload?: { focus_override?: string; difficulty?: number }) {
  const r = await fetch(`${API}/api/imagina/adaptive/plan/${userId}/regenerate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload || {}),
  });
  return r.json();
}

// ─── V15 Adaptive Plan Execution ────────────────────

export async function startAdaptiveExecution(userId: string) {
  const r = await fetch(`${API}/api/imagina/adaptive/execution/${userId}/start`, { method: "POST" });
  if (!r.ok) throw new Error("Cannot start execution");
  return r.json();
}

export async function getLatestAdaptiveExecution(userId: string) {
  const r = await fetch(`${API}/api/imagina/adaptive/execution/${userId}/latest`);
  if (!r.ok) return null;
  return r.json();
}

export async function getAdaptiveExecution(userId: string, executionId: string) {
  const r = await fetch(`${API}/api/imagina/adaptive/execution/${userId}/${executionId}`);
  if (!r.ok) return null;
  return r.json();
}

export async function listAdaptiveExecutions(userId: string) {
  const r = await fetch(`${API}/api/imagina/adaptive/executions/${userId}`);
  return r.json();
}

export async function completeExecutionDay(userId: string, executionId: string, day: number, payload: {
  completed: boolean; duration_minutes_actual?: number; difficulty_rating?: number;
  clarity_rating?: number; fatigue_rating?: number; focus_quality?: number; notes?: string;
}) {
  const r = await fetch(`${API}/api/imagina/adaptive/execution/${userId}/${executionId}/day/${day}/complete`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!r.ok) throw new Error("Cannot complete day");
  return r.json();
}

export async function attachCalibrationToExecutionDay(userId: string, executionId: string, day: number, payload: {
  calibration_session_id: string;
}) {
  const r = await fetch(`${API}/api/imagina/adaptive/execution/${userId}/${executionId}/day/${day}/attach-calibration`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!r.ok) throw new Error("Cannot attach calibration");
  return r.json();
}

export async function closeAdaptiveExecution(userId: string, executionId: string) {
  const r = await fetch(`${API}/api/imagina/adaptive/execution/${userId}/${executionId}/close`, { method: "POST" });
  if (!r.ok) throw new Error("Cannot close execution");
  return r.json();
}

export async function getExecutionAnalysis(userId: string, executionId: string) {
  const r = await fetch(`${API}/api/imagina/adaptive/execution/${userId}/${executionId}/analysis`);
  if (!r.ok) return null;
  return r.json();
}

export async function getAllExecutionsAnalysis(userId: string) {
  const r = await fetch(`${API}/api/imagina/adaptive/executions/${userId}/analysis`);
  return r.json();
}

export async function getLongitudinalProgressReport(userId: string) {
  const r = await fetch(`${API}/api/imagina/adaptive/longitudinal-report/${userId}`);
  return r.json();
}

// ─── V16 Adaptive Optimization Engine ────────────────────

export async function getAdaptiveResponseModel(userId: string) {
  const r = await fetch(`${API}/api/imagina/adaptive/optimization/response-model/${userId}`);
  return r.json();
}

export async function getFatigueAdherenceModel(userId: string) {
  const r = await fetch(`${API}/api/imagina/adaptive/optimization/fatigue-adherence/${userId}`);
  return r.json();
}

export async function getOptimizedNextPlanRecommendation(userId: string) {
  const r = await fetch(`${API}/api/imagina/adaptive/optimization/next-plan/${userId}`);
  return r.json();
}

export async function generateOptimizedAdaptivePlan(userId: string) {
  const r = await fetch(`${API}/api/imagina/adaptive/optimization/generate-plan/${userId}`, { method: "POST" });
  return r.json();
}

export async function compareAdaptiveExecutions(userId: string, executionIds?: string[]) {
  const r = await fetch(`${API}/api/imagina/adaptive/optimization/compare-executions/${userId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ execution_ids: executionIds || null }),
  });
  return r.json();
}

export async function compareTrainingFocuses(userId: string) {
  const r = await fetch(`${API}/api/imagina/adaptive/optimization/compare-focuses/${userId}`);
  return r.json();
}

// ─── V17 N-of-1 Experiment Engine ────────────────────

export async function designNOf1Experiment(userId: string, payload: {
  experiment_type?: string; design?: string; duration_days?: number;
}) {
  const r = await fetch(`${API}/api/imagina/adaptive/experiments/${userId}/design`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!r.ok) throw new Error("Cannot design experiment");
  return r.json();
}

export async function startNOf1Experiment(userId: string, experimentId?: string) {
  const r = await fetch(`${API}/api/imagina/adaptive/experiments/${userId}/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ experiment_id: experimentId }),
  });
  if (!r.ok) throw new Error("Cannot start experiment");
  return r.json();
}

export async function getLatestNOf1Experiment(userId: string) {
  const r = await fetch(`${API}/api/imagina/adaptive/experiments/${userId}/latest`);
  if (!r.ok) return null;
  return r.json();
}

export async function getNOf1Experiment(userId: string, experimentId: string) {
  const r = await fetch(`${API}/api/imagina/adaptive/experiments/${userId}/${experimentId}`);
  if (!r.ok) return null;
  return r.json();
}

export async function listNOf1Experiments(userId: string) {
  const r = await fetch(`${API}/api/imagina/adaptive/experiments/${userId}`);
  return r.json();
}

export async function completeNOf1ExperimentDay(userId: string, experimentId: string, day: number, payload: {
  completed: boolean; duration_minutes_actual?: number; difficulty_rating?: number;
  clarity_rating?: number; fatigue_rating?: number; focus_quality?: number;
  confidence_rating?: number; notes?: string;
}) {
  const r = await fetch(`${API}/api/imagina/adaptive/experiments/${userId}/${experimentId}/day/${day}/complete`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!r.ok) throw new Error("Cannot complete experiment day");
  return r.json();
}

export async function attachNOf1ExperimentCalibration(userId: string, experimentId: string, day: number, calibrationSessionId: string) {
  const r = await fetch(`${API}/api/imagina/adaptive/experiments/${userId}/${experimentId}/day/${day}/attach-calibration`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ calibration_session_id: calibrationSessionId }),
  });
  if (!r.ok) throw new Error("Cannot attach calibration");
  return r.json();
}

export async function closeNOf1Experiment(userId: string, experimentId: string) {
  const r = await fetch(`${API}/api/imagina/adaptive/experiments/${userId}/${experimentId}/close`, { method: "POST" });
  if (!r.ok) throw new Error("Cannot close experiment");
  return r.json();
}

export async function getNOf1ExperimentAnalysis(userId: string, experimentId: string) {
  const r = await fetch(`${API}/api/imagina/adaptive/experiments/${userId}/${experimentId}/analysis`);
  if (!r.ok) return null;
  return r.json();
}

export async function getNOf1EvidenceScore(userId: string, experimentId: string) {
  const r = await fetch(`${API}/api/imagina/adaptive/experiments/${userId}/${experimentId}/evidence-score`);
  return r.json();
}

export async function getNOf1ExperimentReport(userId: string, experimentId: string) {
  const r = await fetch(`${API}/api/imagina/adaptive/experiments/${userId}/${experimentId}/report`);
  if (!r.ok) return null;
  return r.json();
}

// ─── V18 Evidence Dashboard ────────────────────

export async function getEvidenceModel(userId: string) {
  const r = await fetch(`${API}/api/imagina/evidence/${userId}/model`);
  return r.json();
}

export async function getEvidenceQualityAudit(userId: string) {
  const r = await fetch(`${API}/api/imagina/evidence/${userId}/quality-audit`);
  return r.json();
}

export async function getEvidenceTimeline(userId: string) {
  const r = await fetch(`${API}/api/imagina/evidence/${userId}/timeline`);
  return r.json();
}

export async function getEvidenceRecommendation(userId: string) {
  const r = await fetch(`${API}/api/imagina/evidence/${userId}/recommendation`);
  return r.json();
}

export async function generateResearchExportPack(userId: string) {
  const r = await fetch(`${API}/api/imagina/evidence/${userId}/export-pack`, { method: "POST" });
  return r.json();
}

// ─── V19 Imagery Task Battery ────────────────────

export async function getImageryTasks(category?: string) {
  const u = `${API}/api/imagina/imagery/tasks${category ? `?category=${category}` : ""}`;
  const r = await fetch(u);
  return r.json();
}

export async function getImageryTask(taskId: string) {
  const r = await fetch(`${API}/api/imagina/imagery/tasks/${taskId}`);
  if (!r.ok) return null;
  return r.json();
}

export async function startImageryTaskSession(userId: string, taskId: string) {
  const r = await fetch(`${API}/api/imagina/imagery/sessions/${userId}/start/${taskId}`, { method: "POST" });
  if (!r.ok) throw new Error("Cannot start imagery session");
  return r.json();
}

export async function submitImageryTaskRating(sessionId: string, payload: Record<string, number>) {
  const r = await fetch(`${API}/api/imagina/imagery/sessions/${sessionId}/rating`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
  });
  if (!r.ok) throw new Error("Cannot submit rating");
  return r.json();
}

export async function completeImageryTaskSession(sessionId: string) {
  const r = await fetch(`${API}/api/imagina/imagery/sessions/${sessionId}/complete`, { method: "POST" });
  if (!r.ok) throw new Error("Cannot complete session");
  return r.json();
}

export async function getImageryTaskSession(sessionId: string) {
  const r = await fetch(`${API}/api/imagina/imagery/sessions/${sessionId}`);
  if (!r.ok) return null;
  return r.json();
}

export async function listImageryTaskSessions(userId: string) {
  const r = await fetch(`${API}/api/imagina/imagery/sessions/user/${userId}`);
  return r.json();
}

export async function getImageryPhenotype(userId: string) {
  const r = await fetch(`${API}/api/imagina/imagery/phenotype/${userId}`);
  return r.json();
}

export async function getImageryPhenotypeGaps(userId: string) {
  const r = await fetch(`${API}/api/imagina/imagery/gaps/${userId}`);
  return r.json();
}

export async function generateTaskBasedImageryPlan(userId: string, durationDays?: number) {
  const r = await fetch(`${API}/api/imagina/imagery/task-plan/${userId}`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ duration_days: durationDays || 7 }),
  });
  return r.json();
}

// ─── V20 Guided Imagery Session Runtime ────────────────────

export async function getGuidedSessionSchema() {
  const r = await fetch(`${API}/api/imagina/guided/schema`);
  return r.json();
}

export async function startGuidedImagerySession(userId: string, taskId: string) {
  const r = await fetch(`${API}/api/imagina/guided/session/${userId}/start/${taskId}`, { method: "POST" });
  if (!r.ok) throw new Error("Cannot start guided session");
  return r.json();
}

export async function getGuidedSession(sessionId: string) {
  const r = await fetch(`${API}/api/imagina/guided/session/${sessionId}`);
  if (!r.ok) return null;
  return r.json();
}

export async function advanceGuidedSessionPhase(sessionId: string) {
  const r = await fetch(`${API}/api/imagina/guided/session/${sessionId}/advance`, { method: "POST" });
  if (!r.ok) throw new Error("Cannot advance phase");
  return r.json();
}

export async function submitGuidedMicroCheckin(sessionId: string, payload: Record<string, number | string>) {
  const r = await fetch(`${API}/api/imagina/guided/session/${sessionId}/checkin`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
  });
  if (!r.ok) throw new Error("Cannot submit checkin");
  return r.json();
}

export async function pauseGuidedSession(sessionId: string) {
  const r = await fetch(`${API}/api/imagina/guided/session/${sessionId}/pause`, { method: "POST" });
  if (!r.ok) throw new Error("Cannot pause");
  return r.json();
}

export async function resumeGuidedSession(sessionId: string) {
  const r = await fetch(`${API}/api/imagina/guided/session/${sessionId}/resume`, { method: "POST" });
  if (!r.ok) throw new Error("Cannot resume");
  return r.json();
}

export async function completeGuidedSession(sessionId: string) {
  const r = await fetch(`${API}/api/imagina/guided/session/${sessionId}/complete`, { method: "POST" });
  if (!r.ok) throw new Error("Cannot complete");
  return r.json();
}

export async function abortGuidedSession(sessionId: string, reason?: string) {
  const r = await fetch(`${API}/api/imagina/guided/session/${sessionId}/abort`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason: reason || "" }),
  });
  if (!r.ok) throw new Error("Cannot abort");
  return r.json();
}

export async function listGuidedSessions(userId: string) {
  const r = await fetch(`${API}/api/imagina/guided/sessions/${userId}`);
  return r.json();
}

export async function getGuidedSessionReport(sessionId: string) {
  const r = await fetch(`${API}/api/imagina/guided/session/${sessionId}/report`);
  if (!r.ok) return null;
  return r.json();
}

export async function exportGuidedSessionAsTaskRating(sessionId: string) {
  const r = await fetch(`${API}/api/imagina/guided/session/${sessionId}/export-task-rating`, { method: "POST" });
  if (!r.ok) return null;
  return r.json();
}

export async function startNextGuidedTaskFromPlan(userId: string) {
  const r = await fetch(`${API}/api/imagina/guided/plan/${userId}/start-next`, { method: "POST" });
  return r.json();
}

export async function getGuidedPlanProgress(userId: string) {
  const r = await fetch(`${API}/api/imagina/guided/plan/${userId}/progress`);
  return r.json();
}

export async function completeGuidedPlanDay(userId: string, sessionId: string) {
  const r = await fetch(`${API}/api/imagina/guided/plan/${userId}/complete-day/${sessionId}`, { method: "POST" });
  if (!r.ok) throw new Error("Cannot complete plan day");
  return r.json();
}

// ─── V21 Skill Tree & Mastery ────────────────────

export async function getImagerySkillTree() {
  const r = await fetch(`${API}/api/imagina/skill-tree`);
  return r.json();
}

export async function getSkillBranch(dimension: string) {
  const r = await fetch(`${API}/api/imagina/skill-tree/${dimension}`);
  if (!r.ok) return null;
  return r.json();
}

export async function getLongitudinalSkillModel(userId: string) {
  const r = await fetch(`${API}/api/imagina/skill-model/${userId}`);
  return r.json();
}

export async function getMasteryMilestones(userId: string) {
  const r = await fetch(`${API}/api/imagina/mastery-milestones/${userId}`);
  return r.json();
}

export async function getPlateauAnalysis(userId: string) {
  const r = await fetch(`${API}/api/imagina/plateaus/${userId}`);
  return r.json();
}

export async function getDifficultyRecommendation(userId: string, taskId?: string, dimension?: string) {
  const r = await fetch(`${API}/api/imagina/difficulty-recommendation/${userId}`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ task_id: taskId, dimension }),
  });
  return r.json();
}

export async function generateWeeklyProgressReport(userId: string, days?: number) {
  const r = await fetch(`${API}/api/imagina/weekly-progress/${userId}`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ days: days || 7 }),
  });
  return r.json();
}

export async function getWeeklyProgressReport(userId: string) {
  const r = await fetch(`${API}/api/imagina/weekly-progress/${userId}`);
  if (!r.ok) return null;
  return r.json();
}

export async function updateImageryCurriculum(userId: string) {
  const r = await fetch(`${API}/api/imagina/curriculum-update/${userId}`, { method: "POST" });
  return r.json();
}

export async function getCurriculumUpdate(userId: string) {
  const r = await fetch(`${API}/api/imagina/curriculum-update/${userId}`);
  if (!r.ok) return null;
  return r.json();
}

// ─── V22 Scene Simulator ────────────────────

export async function getSceneTemplates(category?: string) {
  const u = `${API}/api/imagina/scenes/templates${category ? `?category=${category}` : ""}`;
  const r = await fetch(u);
  return r.json();
}

export async function getSceneTemplate(templateId: string) {
  const r = await fetch(`${API}/api/imagina/scenes/templates/${templateId}`);
  if (!r.ok) return null;
  return r.json();
}

export async function getSceneTemplateForTask(taskId: string) {
  const r = await fetch(`${API}/api/imagina/scenes/template-for-task/${taskId}`);
  return r.json();
}

export async function updateSceneFromSession(sessionId: string) {
  const r = await fetch(`${API}/api/imagina/scenes/session/${sessionId}/update`, { method: "POST" });
  if (!r.ok) return null;
  return r.json();
}

export async function getLatestSceneState(sessionId: string) {
  const r = await fetch(`${API}/api/imagina/scenes/session/${sessionId}/latest`);
  if (!r.ok) return null;
  return r.json();
}

export async function listSceneStates(sessionId: string) {
  const r = await fetch(`${API}/api/imagina/scenes/session/${sessionId}/states`);
  return r.json();
}

export async function getSceneControlSummary(sessionId: string) {
  const r = await fetch(`${API}/api/imagina/scenes/session/${sessionId}/summary`);
  return r.json();
}

export async function buildGuidedSessionReplay(sessionId: string) {
  const r = await fetch(`${API}/api/imagina/scenes/session/${sessionId}/replay/build`, { method: "POST" });
  if (!r.ok) return null;
  return r.json();
}

export async function getGuidedSessionReplay(sessionId: string) {
  const r = await fetch(`${API}/api/imagina/scenes/session/${sessionId}/replay`);
  if (!r.ok) return null;
  return r.json();
}

export async function getGuidedSessionReplaySummary(sessionId: string) {
  const r = await fetch(`${API}/api/imagina/scenes/session/${sessionId}/replay-summary`);
  return r.json();
}

// ─── V23 Protocol Studio ────────────────────

export async function getBuiltinProtocols() {
  const r = await fetch(`${API}/api/imagina/protocols/builtin`);
  return r.json();
}

export async function getBuiltinProtocol(templateId: string) {
  const r = await fetch(`${API}/api/imagina/protocols/builtin/${templateId}`);
  if (!r.ok) return null;
  return r.json();
}

export async function instantiateBuiltinProtocol(userId: string, templateId: string) {
  const r = await fetch(`${API}/api/imagina/protocols/builtin/${userId}/instantiate/${templateId}`, { method: "POST" });
  if (!r.ok) return null;
  return r.json();
}

export async function createImageryProtocol(userId: string, payload: Record<string, unknown>) {
  const r = await fetch(`${API}/api/imagina/protocols/${userId}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
  return r.json();
}

export async function listImageryProtocols(userId: string) {
  const r = await fetch(`${API}/api/imagina/protocols/user/${userId}`);
  return r.json();
}

export async function startImageryProtocolRunV23(userId: string, protocolId: string) {
  const r = await fetch(`${API}/api/imagina/protocol-runs/${userId}/start/${protocolId}`, { method: "POST" });
  if (!r.ok) throw new Error("Cannot start run");
  return r.json();
}

export async function getImageryProtocolRun(runId: string) {
  const r = await fetch(`${API}/api/imagina/protocol-runs/${runId}`);
  if (!r.ok) return null;
  return r.json();
}

export async function listImageryProtocolRuns(userId: string) {
  const r = await fetch(`${API}/api/imagina/protocol-runs/user/${userId}`);
  return r.json();
}

export async function getActiveImageryProtocolRun(userId: string) {
  const r = await fetch(`${API}/api/imagina/protocol-runs/user/${userId}/active`);
  if (!r.ok) return null;
  return r.json();
}

export async function startNextImageryProtocolBlock(runId: string) {
  const r = await fetch(`${API}/api/imagina/protocol-runs/${runId}/start-next-block`, { method: "POST" });
  if (!r.ok) throw new Error("Cannot start block");
  return r.json();
}

export async function completeImageryProtocolBlock(runId: string, sessionId: string) {
  const r = await fetch(`${API}/api/imagina/protocol-runs/${runId}/complete-block/${sessionId}`, { method: "POST" });
  if (!r.ok) throw new Error("Cannot complete block");
  return r.json();
}

export async function pauseImageryProtocolRun(runId: string) {
  const r = await fetch(`${API}/api/imagina/protocol-runs/${runId}/pause`, { method: "POST" });
  return r.json();
}

export async function resumeImageryProtocolRun(runId: string) {
  const r = await fetch(`${API}/api/imagina/protocol-runs/${runId}/resume`, { method: "POST" });
  return r.json();
}

export async function completeImageryProtocolRunV23(runId: string) {
  const r = await fetch(`${API}/api/imagina/protocol-runs/${runId}/complete`, { method: "POST" });
  return r.json();
}

export async function abortImageryProtocolRun(runId: string, reason?: string) {
  const r = await fetch(`${API}/api/imagina/protocol-runs/${runId}/abort`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ reason: reason || "" }) });
  return r.json();
}

export async function getImageryProtocolBenchmark(runId: string) {
  const r = await fetch(`${API}/api/imagina/protocol-runs/${runId}/benchmark`);
  return r.json();
}

export async function compareImageryProtocolRuns(userId: string, runIds: string[]) {
  const r = await fetch(`${API}/api/imagina/protocol-comparison/${userId}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ run_ids: runIds }) });
  if (!r.ok) return null;
  return r.json();
}

export async function exportImaginaBenchmarkPack(userId: string, runId?: string) {
  const r = await fetch(`${API}/api/imagina/benchmark-export/${userId}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ run_id: runId }) });
  return r.json();
}

export async function getBenchmarkScenarioSchema() {
  const r = await fetch(`${API}/api/imagina/benchmark-sdk/schema`);
  return r.json();
}

export async function getBenchmarkScenarioExample() {
  const r = await fetch(`${API}/api/imagina/benchmark-sdk/example`);
  return r.json();
}

export async function validateBenchmarkScenario(payload: Record<string, unknown>) {
  const r = await fetch(`${API}/api/imagina/benchmark-sdk/validate`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
  return r.json();
}

export async function importBenchmarkScenario(userId: string, payload: Record<string, unknown>) {
  const r = await fetch(`${API}/api/imagina/benchmark-sdk/import/${userId}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
  if (!r.ok) throw new Error("Import failed");
  return r.json();
}

export async function listImportedBenchmarkScenarios(userId: string) {
  const r = await fetch(`${API}/api/imagina/benchmark-sdk/imported/${userId}`);
  return r.json();
}

export async function removeImportedBenchmarkScenario(userId: string, scenarioId: string) {
  const r = await fetch(`${API}/api/imagina/benchmark-sdk/imported/${userId}/${scenarioId}`, { method: "DELETE" });
  return r.json();
}

export async function runImportedClosedLoopScenario(userId: string, scenarioId: string) {
  const r = await fetch(`${API}/api/imagina/benchmark-sdk/run-imported/${userId}/${scenarioId}`, { method: "POST" });
  if (!r.ok) throw new Error("Run failed");
  return r.json();
}

export async function createCustomBenchmarkSuite(userId: string, suiteName: string, scenarioIds: string[], includeBuiltIns?: boolean) {
  const r = await fetch(`${API}/api/imagina/benchmark-sdk/suite/${userId}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ suite_name: suiteName, scenario_ids: scenarioIds, include_built_ins: includeBuiltIns }) });
  return r.json();
}

export async function listCustomBenchmarkSuites(userId: string) {
  const r = await fetch(`${API}/api/imagina/benchmark-sdk/suites/${userId}`);
  return r.json();
}

export async function runCustomBenchmarkSuite(userId: string, suiteId: string) {
  const r = await fetch(`${API}/api/imagina/benchmark-sdk/suites/${userId}/${suiteId}/run`, { method: "POST" });
  if (!r.ok) throw new Error("Run suite failed");
  return r.json();
}

export async function exportBenchmarkSdkPack(userId: string) {
  const r = await fetch(`${API}/api/imagina/benchmark-sdk/export/${userId}`, { method: "POST" });
  return r.json();
}

export async function getPolicyProfileSchema() {
  const r = await fetch(`${API}/api/imagina/policy-lab/schema`);
  return r.json();
}
export async function getPolicyProfileExample() {
  const r = await fetch(`${API}/api/imagina/policy-lab/example`);
  return r.json();
}
export async function getBuiltinPolicyProfiles() {
  const r = await fetch(`${API}/api/imagina/policy-lab/builtins`);
  return r.json();
}
export async function validatePolicyProfile(profile: Record<string, unknown>) {
  const r = await fetch(`${API}/api/imagina/policy-lab/validate`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(profile) });
  return r.json();
}
export async function importPolicyProfile(userId: string, profile: Record<string, unknown>) {
  const r = await fetch(`${API}/api/imagina/policy-lab/import/${userId}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(profile) });
  return r.json();
}
export async function listPolicyProfiles(userId: string) {
  const r = await fetch(`${API}/api/imagina/policy-lab/profiles/${userId}`);
  return r.json();
}
export async function runPolicyProfileBenchmark(userId: string, policyId: string) {
  const r = await fetch(`${API}/api/imagina/policy-lab/run/${userId}/${policyId}`, { method: "POST" });
  return r.json();
}
export async function runPolicyProfileBenchmarkMatrix(userId: string, policyIds?: string[]) {
  const r = await fetch(`${API}/api/imagina/policy-lab/run-matrix/${userId}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ policy_ids: policyIds }) });
  return r.json();
}
export async function getLatestPolicyBenchmarkMatrix(userId: string) {
  const r = await fetch(`${API}/api/imagina/policy-lab/latest-matrix/${userId}`);
  return r.json();
}
export async function buildPolicyLeaderboard(userId: string) {
  const r = await fetch(`${API}/api/imagina/policy-lab/leaderboard/${userId}`, { method: "POST" });
  return r.json();
}
export async function getPolicyLeaderboard(userId: string) {
  const r = await fetch(`${API}/api/imagina/policy-lab/leaderboard/${userId}`);
  return r.json();
}
export async function exportPolicyLabPack(userId: string) {
  const r = await fetch(`${API}/api/imagina/policy-lab/export/${userId}`, { method: "POST" });
  return r.json();
}
