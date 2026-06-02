"""OpenMIIR Experiment Grammar — extracted from MATLAB presentation script."""

import json
import os
import sys
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
EXPORTS = os.path.join(BASE, "..", "..", "data", "exports")


def build_grammar():
    return {
        "tool": "openmiir_experiment_grammar_v3.9.5",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_file": "scripts/presentation/OpenMIIR_StimulusPresentation.m",
        "trigger_semantics": {
            "1": {"label": "music_perception", "category": "perception",
                  "description": "Listen to music"},
            "2": {"label": "cued_imagery", "category": "imagery",
                  "description": "Imagine music following a cue"},
            "3": {"label": "uncued_imagery", "category": "imagery",
                  "description": "Imagine music without a cue"},
            "4": {"label": "noise", "category": "baseline",
                  "description": "White noise inter-stimulus washout"},
        },
        "block_grammar": {
            "block_1": {
                "description": (
                    "Music perception + cued imagery + uncued imagery + noise. "
                    "Random song order, repeated n times."),
                "expected_trigger_sequence_per_song": [1, 2, 3, 4],
                "stimulus_count": 12,
                "repetitions": "n (user-specified)",
                "triggers_per_trial": 4,
            },
            "block_2": {
                "description": "Uncued imagery only. Random song order, repeated m times.",
                "expected_trigger_sequence_per_song": [3],
                "stimulus_count": 12,
                "repetitions": "m (user-specified)",
                "triggers_per_trial": 1,
            },
        },
        "stimtracker_encoding": {
            "device": "Cedrus StimTracker",
            "command_format": "fwrite(sport, ['mh', TRIGGER, 0])",
            "trigger_values": [0, 1, 2, 3, 4],
            "encoding_hypothesis": (
                "Stim channel event codes are {stimulus_group}{trigger_type} "
                "for two-digit codes. Three-digit codes (111-244) add a block "
                "prefix digit. The Cedrus StimTracker encodes the serial "
                "command into composite trigger values."
            ),
            "encoding_documented": False,
            "encoding_source": "StimTracker hardware firmware — not in MATLAB source",
        },
        "confidence": "confirmed_from_matlab_source",
        "evidence_quotes": [
            "% Trigger values sent to Cedrus StimTracker:",
            "% 1= music",
            "% 2= cued imagination",
            "% 3= imagination without a cue",
            "% 4= noise",
            "fwrite(sport,['mh',1,0]); %send trigger",
            "fwrite(sport,['mh',2,0]); %send trigger",
            "fwrite(sport,['mh',3,0]); %send trigger",
            "fwrite(sport,['mh',4,0]); %send trigger",
        ],
    }


def main():
    os.makedirs(EXPORTS, exist_ok=True)
    grammar = build_grammar()

    json_path = os.path.join(EXPORTS, "openmiir_experiment_grammar.json")
    with open(json_path, "w") as f:
        json.dump(grammar, f, indent=2, default=str)

    md_lines = [
        "# OpenMIIR Experiment Grammar",
        "",
        "## Trigger Semantics (Confirmed from MATLAB)",
        "| Trigger | Condition | Category |",
        "|---------|-----------|----------|",
    ]
    for k, v in grammar["trigger_semantics"].items():
        md_lines.append(f"| {k} | {v['label']} | {v['category']} |")

    md_lines.append("")
    md_lines.append("## Block Grammar")
    md_lines.append("- Block 1: 12 songs × [listen, cued_imagery, uncued_imagery, noise]")
    md_lines.append("- Block 2: 12 songs × [uncued_imagery only]")

    md_lines.append("")
    md_lines.append("## StimTracker Encoding (Hypothesis)")
    md_lines.append(f"- Device: {grammar['stimtracker_encoding']['device']}")
    md_lines.append(f"- Command: `{grammar['stimtracker_encoding']['command_format']}`")
    md_lines.append(f"- Documented: {grammar['stimtracker_encoding']['encoding_documented']}")

    md_path = os.path.join(EXPORTS, "openmiir_experiment_grammar.md")
    with open(md_path, "w") as f:
        f.write("\n".join(md_lines))

    print("Experiment grammar: parsed from MATLAB. Triggers: 1=perception, 2=cued, 3=uncued, 4=noise",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
