# IMAGINA Program Status

> Generated from `science/registry/` by `python -m app.cli.science_ledger --write`.
> Do not edit by hand. Change the registry or the result artifact instead.

**Operating ceiling:** `L1_BEHAVIORAL_ASSISTED`  
**Registry reviewed:** 2026-10-29

## Gates

| Gate | Name | Status | Canonical artifact | Note |
| --- | --- | --- | --- | --- |
| C1 | Neural-behavioural alignment | `NULL` | `c1.final` | Null on incremental validity; mechanism unresolved. |
| C2 | Neural content and state disentanglement | `NULL` | `c2.final` | Null content and transfer within sensitivity. |
| C3 | Zero-shot imagery transfer | `NULL` | `c3.final` | Perception passes; imagery transfer null. |
| C3M | Cross-session alignment mechanism | `NULL` | `c3m.final` | Alignment works for seen images; imagery remains degenerate. |
| C3XAT_R1 | Atlas imagery qualification (replication 1) | `LIMITED` | `c3xat.r1.final` | 1/6 subject pass; C3XAG not authorized. |
| ANIMUS_P1 | ANIMUS closed-loop vertical slice | `PASS` | `animus.p1` | Engineering pass under simulation; not a human validation. |
| ANIMUS_P2 | Perception decoder confirmation | `BLOCKED` | `animus.p2r` | Confirmatory compute blocked; pilot only. |
| ANIMUS_P3_SIM | Source-monitoring Stage 0 simulation | `PASS` | `animus.p3.sim` | Simulation-only design gate for the Source and Imagination Monitor. A PASS means parameter recovery and the coverage constraints are acceptable in simulation; it is not human validation and does not authorize a measurement claim. |
| ANIMUS_P3_POWER | Source-monitoring Stage 1 power check | `PASS` | `animus.p3.power` | Simulation-only planning gate. A PASS means the planned N=180 has at least 80% power for the reliability lower-bound target under the stated approximation; it is not human evidence. |

## Claims

| Claim | Status | Ceiling | n | Evidence | Statement |
| --- | --- | --- | --- | --- | --- |
| `claim.behavioral_imagery_assistance` | `LIMITED` | `L1_BEHAVIORAL_ASSISTED` |  | `animus.p1` | The platform can scaffold scene authoring and adaptive behavioural practice and can report uncertainty, without claiming that it improves imagery strength or clinical outcomes. |
| `claim.scene_threshold_measurement` | `UNVALIDATED` | `L1_BEHAVIORAL_ASSISTED` |  | none | Scene Threshold estimates a within-scene 2-AFC discrimination threshold and d-prime with calibrated uncertainty. |
| `claim.scene_reconstruction_accuracy` | `UNVALIDATED` | `L1_BEHAVIORAL_ASSISTED` |  | `c3xat.r1.final` | The epistemic interview reconstructs probe-variable beliefs with reported uncertainty, not a picture of what a person imagined. |
| `claim.perception_neural_content` | `PILOT` | `L2_NEURAL_CONTENT` | 2 | `animus.p2`, `animus.p2r` | A perception-trained decoder can recover seen-image content above chance in a held-out subject under the sealed ANIMUS protocol. |
| `claim.imagery_neural_content` | `BLOCKED` | `L2_NEURAL_CONTENT` | 1 | `c3.final`, `c3m.final`, `c3xat.r1.final` | A decoder can recover imagined scene content above chance from held-out neural data, beyond session, cue, and state confounds. |
| `claim.neural_geometry` | `BLOCKED` | `L2_NEURAL_CONTENT` |  | `c3xat.r1.final` | Imagery-related neural geometry can be estimated and used to authorize a new acquisition or closed-loop geometry experiment. |
| `claim.legacy_pid_iqi` | `DEPRECATED` | `L1_BEHAVIORAL_ASSISTED` |  | none | PID and IQI are composite proxy scores that summarize simulated or demonstrated session signals. |
| `claim.clinical_or_diagnostic` | `BLOCKED` | `L3_CLOSED_LOOP` |  | none | The platform diagnoses, treats, or clinically validates a mental-health or neurological condition. |
| `claim.source_monitoring_measurement` | `UNVALIDATED` | `L1_BEHAVIORAL_ASSISTED` |  | none | The Source and Imagination Monitor estimates source discrimination and source calibration for seen, imagined, described, and new content, with reported uncertainty and explicit insufficient-data states. |
| `claim.source_monitoring_training` | `BLOCKED` | `L1_BEHAVIORAL_ASSISTED` |  | none | Adaptive source-monitoring feedback improves source calibration or source discrimination beyond a yoked active control. |
| `claim.source_monitoring_clinical` | `BLOCKED` | `L3_CLOSED_LOOP` |  | none | The Source and Imagination Monitor diagnoses, predicts, or treats a clinical condition. |

## Supersession and conflicts

- `animus.p2` (`ANIMUS_P2_PERCEPTION_DECODER_VALIDATED` -> `PILOT`) is superseded by `animus.p2r`.
- `animus.p2e` (`ANIMUS_P2_BLOCKED_ROI_SPATIAL_PROVENANCE` -> `BLOCKED`) is superseded by `animus.p2r`.
- `c3.realdata` (`SUPERSEDED_BY_AUTHORITATIVE_ROW_MAPPING_RESOLUTION` -> `SUPERSEDED`) is superseded by `c3.final`.
- `c3xat.r1.blocked1` (`C3XAT_R1_BLOCKED_EXECUTION_INCOMPLETE` -> `BLOCKED`) is superseded by `c3xat.r1.final`.
- `c3xat.r1.blocked2` (`C3XAT_R1_BLOCKED_PERCEPTION_ESTIMAND` -> `BLOCKED`) is superseded by `c3xat.r1.final`.

## Provenance

| Artifact | Gate | Authority | Mapped status | SHA-256 | Bytes |
| --- | --- | --- | --- | --- | --- |
| `animus.p1` | ANIMUS_P1 | canonical | `PASS` | `3568af04d443e438cd148f04c603a451c7416bcc999dbf4f8bb2d5bf1e7424d2` | 1163 |
| `animus.p2` | ANIMUS_P2 | historical | `PILOT` | `e268f6acd4df1992c8e803bb0a7f19744f5cdb9c66c862b4d6ac9966b16bfcca` | 2005 |
| `animus.p2e` | ANIMUS_P2 | historical | `BLOCKED` | `b1dce7a92e27901662632910d6cad3a508dff9c9e1edf76d1a750553232a7541` | 2570 |
| `animus.p2r` | ANIMUS_P2 | canonical | `BLOCKED` | `173620c625e8cb70338d4806b45fab428fddb82c498f36a35ba98382bd4d9cab` | 1308 |
| `animus.p3.power` | ANIMUS_P3_POWER | canonical | `PASS` | `5d44b4362cc2989484a2e566bbb1ec29a6baba2d1011101f1df4ebc5d47353f3` | 996 |
| `animus.p3.sim` | ANIMUS_P3_SIM | canonical | `PASS` | `68a1a41df0f78b21e787b42bb6ed3eb3e184b7da2cec55c0005f9bb640dd79cc` | 1934 |
| `c1.final` | C1 | canonical | `NULL` | `1f412b5216d37664a54078ace6e9bc5aaf084ef24830607732a77d1006632c3b` | 9737 |
| `c2.final` | C2 | canonical | `NULL` | `e02e6c961302614380333e572d221b17bc11d8f14603d412784e709f95998a2e` | 8804 |
| `c3.final` | C3 | canonical | `NULL` | `6073ec1c8aa130ef1aa06e73c87db1df571edbd49986d2e6d5e2e57113c0fc60` | 5650 |
| `c3.realdata` | C3 | historical | `SUPERSEDED` | `ca552078dd9d034e97350cf835d86997f82702e5cc31c56f2dc2f4b971bf0b5e` | 3849 |
| `c3m.final` | C3M | canonical | `NULL` | `a53d926c0c4981594d68e656fa5f1a68fe55130ae49cba46407bbfae39cb6154` | 4637 |
| `c3xat.r1.blocked1` | C3XAT_R1 | historical | `BLOCKED` | `db6b5ef0baf650ad33acf93ee2cea449ac1a0526facebea98d01c98e2ad2e3f0` | 2680 |
| `c3xat.r1.blocked2` | C3XAT_R1 | historical | `BLOCKED` | `ff4a9880f75c182c90624a893b47d6373851ba48f0167ae0a1fead8408d112f1` | 3110 |
| `c3xat.r1.final` | C3XAT_R1 | canonical | `LIMITED` | `cf0a8aecaf61b3117a7fcfb59ab534bfe42da41caeb4fadf39beade5c136126c` | 7570 |

## What this document does not establish

- It does not validate a claim; it records the current evidence and the claim boundary.
- It does not authorize human data collection, clinical use, or a new acquisition.
- It does not resolve a paused or blocked confirmatory analysis by prose.
