# Ethics and Safety

## Core Principles

1. **No mind reading.** IMAGINA does not decode, reconstruct, or infer the content of thoughts or mental images.
2. **Not medical.** IMAGINA is not a medical device, diagnostic tool, or therapeutic intervention.
3. **Local-first privacy.** All data stays on the user's machine. No cloud accounts, no telemetry, no external API calls.
4. **Transparent limitations.** Every metric is labeled as experimental and proxy-based.
5. **User autonomy.** Users can stop any session at any time without consequence.

## Privacy Model

- All session data is stored in local SQLite.
- No data is transmitted to external servers.
- No user authentication or tracking.
- Users can delete their data by removing the SQLite database file.

## Safety Measures

- **Fatigue monitoring:** Sessions warn when fatigue estimates are high.
- **Session time limits:** Default maximum of 20 minutes.
- **Dissociation keyword detection:** Simple keyword matching in user notes triggers safety warnings.
- **Overeffort detection:** High effort + high fatigue triggers a simplification cue.
- **Visible disclaimers:** Present on landing page, session start, and in reports.
- **Research mode disclosure:** Experiment protocols and catch trials must be presented as validation controls, not hidden manipulation.
- **Local-first profiles:** User progress data is stored locally without authentication or cloud sync.
- **EEG boundary:** Future LSL integration is experimental and non-clinical unless separately validated and regulated.

## Safety Disclaimer

This software is not medical advice. It is not a substitute for professional mental health care. If you experience distress, dizziness, dissociation, panic, or any uncomfortable sensations during use, stop the session immediately. Consult a healthcare professional if symptoms persist.

## Responsible Development

- No external LLM/AI APIs are used (no risk of hallucinated medical claims).
- All prompt text is deterministic templates reviewed for safety.
- No manipulation, dark patterns, or gamification of distress.
- Open documentation of all formulas and assumptions.
