# Experiment Mode

IMAGINA V2 adds lightweight local experiment protocols.

Supported protocol families:

- Adaptive curriculum.
- Fixed curriculum.
- Visual-only feedback.
- Guided prompt feedback.
- Self-report-only mode.
- Simulated-signal-assisted mode.
- Catch-trial control.

Catch trials are for research mode only. They should be disclosed as control feedback periods used for validation. Normal demo mode should not imply deception or hidden manipulation.

All experiment outputs remain experimental proxy data and are not clinical.

## End-to-End Run Flow

1. Create a local profile or use an anonymous participant label.
2. Select a protocol on `/experiments`.
3. Create an experiment run.
4. Use **Create Next Session** to generate a linked session with protocol metadata.
5. Complete calibration and run the session normally.
6. Stop the session; the run records the completed session and profile progress updates locally.
7. Continue until all planned sessions are complete.
8. Open linked session reports or export `/api/exports/experiment/{run_id}/summary.json`.

Experiment runs track planned sessions, completed sessions, current step, condition, and catch-trial markers. Session reports include the experiment run id when linked.

## Ethical Framing

Catch trials may hold feedback constant for validation only in research mode. They must be disclosed before participation. IMAGINA does not infer hidden mental content from catch-trial behavior.
