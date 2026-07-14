"use client";

import AppShell from "@/components/layout/AppShell";

const CONSTRUCTS = [
  { name: "Imagery Precision", domain: "imagery_precision", objective: true,
    description: "How accurately imagined visual features can be reconstructed" },
  { name: "Imagery Control", domain: "imagery_control", objective: true,
    description: "How accurately a person can intentionally manipulate a represented feature" },
  { name: "Imagery Stability", domain: "imagery_stability", objective: true,
    description: "How consistently the representation is maintained across a delay" },
  { name: "Metacognitive Calibration", domain: "metacognitive_calibration", objective: true,
    description: "Correspondence between confidence and objective correctness" },
  { name: "Subjective Vividness", domain: "subjective_vividness", objective: false,
    description: "Self-reported imagery vividness (secondary construct only)" },
  { name: "Perceptual/Motor Control", domain: "perceptual_motor_control", objective: true,
    description: "Negative control: perceptual matching with target visible" },
];

const TASK_BATTERY = [
  { family: "Feature Reconstruction", id: "feature_reconstruction",
    description: "Fixation → target → mask → imagery → reconstruct → confidence" },
  { family: "Imagery Manipulation", id: "imagery_manipulation",
    description: "Base stimulus → mental transform → reconstruct transformed target" },
  { family: "Delayed Imagery", id: "delayed_imagery",
    description: "Multiple retention delays — immediate vs. delayed reconstruction" },
  { family: "Perceptual Control", id: "perceptual_control",
    description: "Target visible during matching — isolates motor/perceptual skill" },
];

const ENDPOINTS = [
  { id: "composite_reconstruction_error", role: "primary", objective: true,
    direction: "lower_is_better", version: "1.0" },
  { id: "orientation_reconstruction_error", role: "key_secondary", objective: true,
    direction: "lower_is_better", version: "1.0" },
  { id: "hue_reconstruction_error", role: "key_secondary", objective: true,
    direction: "lower_is_better", version: "1.0" },
  { id: "imagery_manipulation_accuracy", role: "key_secondary", objective: true,
    direction: "lower_is_better", version: "1.0" },
  { id: "delayed_stability_degradation", role: "key_secondary", objective: true,
    direction: "lower_is_better", version: "1.0" },
  { id: "metacognitive_calibration", role: "key_secondary", objective: true,
    direction: "higher_is_better", version: "1.0" },
  { id: "subjective_vividness", role: "subjective_secondary", objective: false,
    direction: "higher_is_better", version: "1.0" },
  { id: "perceptual_matching_error", role: "negative_control", objective: true,
    direction: "lower_is_better", version: "1.0" },
  { id: "simple_motor_latency", role: "negative_control", objective: true,
    direction: "lower_is_better", version: "1.0" },
];

export default function MeasurementPage() {
  return (
    <AppShell>
      <div className="max-w-5xl mx-auto space-y-8 p-6">
        <div className="bg-amber-50 border border-amber-300 rounded-lg p-4 text-sm text-amber-900">
          <strong>Research Disclaimer:</strong> Synthetic engineering and statistical
          validation only. No human efficacy or neuroscientific claim.
        </div>

        <h1 className="text-2xl font-bold">Measurement Workbench</h1>

        <section>
          <h2 className="text-xl font-semibold mb-3">Construct Map</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {CONSTRUCTS.map((c) => (
              <div key={c.domain} className={`border rounded-lg p-3 ${
                c.objective ? "border-blue-200 bg-blue-50" : "border-gray-200 bg-gray-50"
              }`}>
                <div className="flex items-center gap-2">
                  <span className={`text-xs px-2 py-0.5 rounded ${
                    c.objective ? "bg-blue-200 text-blue-800" : "bg-gray-200 text-gray-600"
                  }`}>
                    {c.objective ? "Objective" : "Subjective"}
                  </span>
                  <span className="font-medium">{c.name}</span>
                </div>
                <p className="text-sm text-gray-600 mt-1">{c.description}</p>
              </div>
            ))}
          </div>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-3">Task Battery</h2>
          <div className="space-y-2">
            {TASK_BATTERY.map((t) => (
              <div key={t.id} className="border rounded-lg p-3 bg-white">
                <span className="font-medium">{t.family}</span>
                <span className="text-xs text-gray-500 ml-2">({t.id})</span>
                <p className="text-sm text-gray-600 mt-1">{t.description}</p>
              </div>
            ))}
          </div>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-3">Endpoint Definitions</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="bg-gray-100">
                  <th className="text-left p-2 border">Endpoint</th>
                  <th className="text-left p-2 border">Role</th>
                  <th className="text-left p-2 border">Type</th>
                  <th className="text-left p-2 border">Direction</th>
                  <th className="text-left p-2 border">Version</th>
                </tr>
              </thead>
              <tbody>
                {ENDPOINTS.map((ep) => (
                  <tr key={ep.id} className="hover:bg-gray-50">
                    <td className="p-2 border font-mono text-xs">{ep.id}</td>
                    <td className="p-2 border">
                      <span className={`text-xs px-1.5 py-0.5 rounded ${
                        ep.role === "primary" ? "bg-green-100 text-green-800" :
                        ep.role === "negative_control" ? "bg-red-100 text-red-800" :
                        ep.role === "subjective_secondary" ? "bg-gray-100 text-gray-600" :
                        "bg-blue-100 text-blue-800"
                      }`}>{ep.role}</span>
                    </td>
                    <td className="p-2 border">{ep.objective ? "Objective" : "Subjective"}</td>
                    <td className="p-2 border text-xs">{ep.direction}</td>
                    <td className="p-2 border">{ep.version}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </AppShell>
  );
}
