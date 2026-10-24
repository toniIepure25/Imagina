"use client";

import { useState } from "react";

interface ConsentGateProps {
  studyTitle: string;
  consentVersion: string;
  onConsent: () => void;
  onDecline: () => void;
}

export default function ConsentGate({ studyTitle, consentVersion, onConsent, onDecline }: ConsentGateProps) {
  const [accepted, setAccepted] = useState(false);

  return (
    <div className="max-w-2xl mx-auto p-8 bg-white/5 rounded-2xl border border-white/10">
      <h2 className="text-2xl font-bold mb-4">Informed Consent</h2>
      <p className="text-sm text-gray-400 mb-2">Study: {studyTitle}</p>
      <p className="text-sm text-gray-400 mb-6">Consent version: {consentVersion}</p>

      <div className="space-y-4 text-sm text-gray-300 mb-6">
        <div className="p-4 bg-white/5 rounded-lg">
          <h3 className="font-semibold text-white mb-2">About This Study</h3>
          <p>
            IMAGINA is a research prototype for closed-loop mental imagery training.
            It estimates proxy metrics related to attention, self-reported vividness,
            behavioral consistency, and simulated signal patterns. It does not read
            your mind, decode your dreams, or diagnose any condition.
          </p>
        </div>

        <div className="p-4 bg-white/5 rounded-lg">
          <h3 className="font-semibold text-white mb-2">What You Will Do</h3>
          <p>
            You will perform mental imagery tasks (imagining visual scenes) while
            the system provides adaptive visual feedback. You will rate your
            experience after each trial. Sessions last approximately 15-20 minutes.
          </p>
        </div>

        <div className="p-4 bg-white/5 rounded-lg">
          <h3 className="font-semibold text-white mb-2">Risks and Safeguards</h3>
          <p>
            Mental imagery practice may cause mild fatigue. The system monitors
            estimated fatigue and will suggest rest periods. You may stop at any
            time without penalty.
          </p>
        </div>

        <div className="p-4 bg-white/5 rounded-lg">
          <h3 className="font-semibold text-white mb-2">Privacy</h3>
          <p>
            All data is stored locally on this computer. No data is sent to
            external servers. Your identity is recorded only as a pseudonym.
          </p>
        </div>

        <div className="p-4 bg-white/5 rounded-lg">
          <h3 className="font-semibold text-white mb-2">Withdrawal</h3>
          <p>
            You may withdraw from the study at any time. Your data will be
            retained up to the point of withdrawal but will not be included
            in final analyses if you request its removal.
          </p>
        </div>
      </div>

      <label className="flex items-center gap-3 mb-6 cursor-pointer">
        <input
          type="checkbox"
          checked={accepted}
          onChange={(e) => setAccepted(e.target.checked)}
          className="w-5 h-5 rounded bg-white/10 border-white/20"
        />
        <span className="text-sm">
          I have read and understood the above information. I voluntarily agree to participate.
        </span>
      </label>

      <div className="flex gap-4">
        <button
          onClick={onConsent}
          disabled={!accepted}
          className="px-6 py-3 bg-emerald-600 hover:bg-emerald-700 disabled:bg-gray-700 disabled:text-gray-500 rounded-xl font-medium transition-colors"
        >
          I Consent
        </button>
        <button
          onClick={onDecline}
          className="px-6 py-3 bg-white/10 hover:bg-white/20 rounded-xl font-medium transition-colors"
        >
          Decline
        </button>
      </div>
    </div>
  );
}
