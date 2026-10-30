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
| ANIMUS_P4_ART_SIM | Active Reality Testing Stage 0B simulation | `PASS` | `animus.p4.art.sim` | Simulation-only design gate. A PASS means the EIG agent is above chance and its query choices are efficient under the stated model; it is not human validation and does not authorize a measurement claim. |
| ANIMUS_P4_ART_POWER | Active Reality Testing Stage 2 power check | `PASS` | `animus.p4.art.power` | Simulation-only planning gate. A PASS means N=180 has at least 80% power for the ARTE reliability lower-bound target under the stated approximation; it is not human evidence. |
| ANIMUS_P4_ART_RECOVERY | Active Reality Testing policy recovery | `PASS` | `animus.p4.art.recovery` | Simulation-only model-recovery gate. A PASS means the policy parameters are recovered within the stated tolerance conditional on the known EIG feature matrix; it does not validate the task or the full hierarchical measurement model. |
| ANIMUS_P5_CRT_SIM | Counterfactual Reality Testing Stage 0C simulation | `LIMITED` | `animus.p5.crt.sim` | Simulation-only design gate. A PASS means the prospective-prediction contrast and the meta-EIG policy clear the stated thresholds in simulation; it is not human validation and does not authorize a measurement claim. A REVIEW preserves the prediction contrast as provisional and blocks the active-selection claim. |
| ANIMUS_P5_CRT_RECOVERY | Counterfactual Reality Testing policy and precision recovery | `PASS` | `animus.p5.crt.recovery` | Simulation-only recovery gate. A PASS means policy, prediction-precision, and imagination-inflation parameters are recovered within the stated tolerance under the Stage 0C fixed-parameter conditions; it does not validate the task or the human analysis model. |
| ANIMUS_P5_CRT_POWER | Counterfactual Reality Testing Stage 1 power check | `PASS` | `animus.p5.crt.power` | Simulation-only planning gate. A PASS means N=180 has at least 80% power for the reliability lower-bound target under the stated approximation; it is not human evidence. |
| ANIMUS_P5_CRT_THEORY | Counterfactual Reality Testing Stage 0D model-signature separability | `PASS` | `animus.p5.crt.theory` | Simulation-only design-identifiability gate. A PASS means the five competing theory signatures are separable under the stated measurement noise. It is not a fit to human data and does not establish that any model is true. |
| ANIMUS_P5_CRT_SPECIFICITY | Counterfactual Reality Testing specificity and active-selection controls | `LIMITED` | `animus.p5.crt.specificity.belief` | Simulation-only control gate, now canonicalized on belief-based prediction. The historical oracle artifact is preserved but superseded; Stage 0E showed that the diagnostic-specificity advantage did not reproduce when the participant predicted from the current source posterior. The current status is LIMITED. Not human evidence. |
| ANIMUS_P5_CRT_MODEL_REPAIR | Counterfactual Reality Testing belief-based prediction repair | `PASS` | `animus.p5.crt.model_repair` | Simulation-only model-repair gate. A PASS means oracle inflation is quantified, the belief arm predicts from the current source posterior, the source is updated from the outcome only, and the nested posterior PIT calibration check passes. A PASS is design evidence, not human validation and not authorization for a measurement claim. |
| ANIMUS_P5_CRT_RECOVERY_BELIEF | Counterfactual Reality Testing belief-readout recovery and conditional SBC | `PASS` | `animus.p5.crt.recovery.belief` | Simulation-only identifiability gate for the repaired belief readout. A PASS requires conditional parameter recovery of pi (relative RMSE, bias, correlation), a uniform conditional SBC rank histogram, and above-threshold recovery of M0 versus M2. d, guessing, and response bias are fixed; this is not full hierarchical SBC and not human evidence. |
| ANIMUS_P5_CRT_COUNTERFACTUAL | Counterfactual Reality Testing dual-hypothesis prediction | `LIMITED` | `animus.p5.crt.counterfactual` | Simulation-only construct gate. A PASS requires dual diagnostic prediction to improve accuracy over a single prediction and a dual non-diagnostic prediction on the same test sequence. A REVIEW means the counterfactual label is not yet earned; the construct remains prospective reality testing. |
| ANIMUS_P5_CRT_POLICY | Counterfactual Reality Testing policy competition | `LIMITED` | `animus.p5.crt.policy` | Simulation-only policy gate. A PASS requires meta-EIG selection to exceed both cost-only and the best competing policy. A REVIEW means the normative meta-EIG claim is descriptive only. |
| ANIMUS_P5_CRT_PSYCHOMETRIC | Counterfactual Reality Testing test-facet reliability | `PASS` | `animus.p5.crt.psychometric` | Simulation-only test-facet reliability gate. A PASS means every simulated test facet clears the pre-specified relative-reliability floor at two occasions. It is not a human reliability estimate. |
| ANIMUS_P5_CRT_GTHEORY | Counterfactual Reality Testing generalizability decision study | `PASS` | `animus.p5.crt.gtheory` | Simulation-only variance-component and decision-study gate. A PASS means the simulated person variance supports the stated relative-reliability target at two occasions; it is not an estimate of human reliability. |
| ANIMUS_P5_CRT_CALIBRATION | Counterfactual Reality Testing test-likelihood calibration design | `PASS` | `animus.p5.crt.calibration` | Simulation-only calibration gate. A PASS means at least four tests have a strong simulated seen-versus-imagined likelihood ratio and the fluency trap remains non-diagnostic. A human calibration sample must freeze the likelihood table before confirmatory data collection. |

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
| `claim.active_reality_testing_measurement` | `UNVALIDATED` | `L1_BEHAVIORAL_ASSISTED` |  | none | Active Reality Testing estimates the efficiency with which a person selects source-diagnostic evidence before judging whether an experience was seen, imagined, described, or new, with reported uncertainty and explicit insufficient-data states. |
| `claim.active_reality_testing_training` | `BLOCKED` | `L1_BEHAVIORAL_ASSISTED` |  | none | Adaptive Active Reality Testing feedback improves source-inquiry efficiency or source calibration beyond a yoked active control. |
| `claim.active_reality_testing_clinical` | `BLOCKED` | `L3_CLOSED_LOOP` |  | none | Active Reality Testing diagnoses, predicts, or treats a clinical condition. |
| `claim.source_monitoring_training` | `BLOCKED` | `L1_BEHAVIORAL_ASSISTED` |  | none | Adaptive source-monitoring feedback improves source calibration or source discrimination beyond a yoked active control. |
| `claim.source_monitoring_clinical` | `BLOCKED` | `L3_CLOSED_LOOP` |  | none | The Source and Imagination Monitor diagnoses, predicts, or treats a clinical condition. |
| `claim.counterfactual_reality_testing_measurement` | `UNVALIDATED` | `L1_BEHAVIORAL_ASSISTED` |  | none | Counterfactual Reality Testing estimates whether a person prospectively predicts the consequence of a source-diagnostic test and uses the observed outcome to revise a seen/imagined/described/new attribution, with reported uncertainty and explicit low-information states. The prediction is a belief-based readout and policy signal, not independent source evidence. |
| `claim.counterfactual_reality_testing_training` | `BLOCKED` | `L1_BEHAVIORAL_ASSISTED` |  | none | Counterfactual Reality Testing training improves source calibration or prediction accuracy beyond a yoked prediction control. |
| `claim.counterfactual_reality_testing_clinical` | `BLOCKED` | `L3_CLOSED_LOOP` |  | none | Counterfactual Reality Testing diagnoses, predicts, or treats a clinical condition. |

## Supersession and conflicts

- `animus.p2` (`ANIMUS_P2_PERCEPTION_DECODER_VALIDATED` -> `PILOT`) is superseded by `animus.p2r`.
- `animus.p2e` (`ANIMUS_P2_BLOCKED_ROI_SPATIAL_PROVENANCE` -> `BLOCKED`) is superseded by `animus.p2r`.
- `animus.p5.crt.specificity` (`CRT_STAGE0D_SPECIFICITY_PASS` -> `PASS`) is superseded by `animus.p5.crt.specificity.belief`.
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
| `animus.p4.art.power` | ANIMUS_P4_ART_POWER | canonical | `PASS` | `3e68343aa70239b7fcd1518708675a3bca61baa5dc47fd56453681bfa253fc1e` | 996 |
| `animus.p4.art.recovery` | ANIMUS_P4_ART_RECOVERY | canonical | `PASS` | `6c6da963106c4ce4219794c738624ceb3a24e0a5c7c841a6e8b7a74f8f787674` | 5986 |
| `animus.p4.art.sim` | ANIMUS_P4_ART_SIM | canonical | `PASS` | `812b6001986b50debfd2ddeb7dc66770f4a5ced641e2529c7517199fd6acdb4d` | 1582 |
| `animus.p5.crt.calibration` | ANIMUS_P5_CRT_CALIBRATION | canonical | `PASS` | `e27dc33439d19b89e428fdb4272c687af7e7be103b985b687ff6a142c1b80373` | 3419 |
| `animus.p5.crt.counterfactual` | ANIMUS_P5_CRT_COUNTERFACTUAL | canonical | `LIMITED` | `477568efd5c11da21fa7794594608ee9f163fb2334d20f395d753c6a03a4a03a` | 3902 |
| `animus.p5.crt.gtheory` | ANIMUS_P5_CRT_GTHEORY | canonical | `PASS` | `d50038a0cbd58732ba0409467dfd217e472aca80153ee3005ed3956dfc5ae7fc` | 1932 |
| `animus.p5.crt.model_repair` | ANIMUS_P5_CRT_MODEL_REPAIR | canonical | `PASS` | `4b4dc2153f97b07bcbd9d4424bf76dbba2f4196714efb050f4fba82cc8c8fb51` | 2669 |
| `animus.p5.crt.policy` | ANIMUS_P5_CRT_POLICY | canonical | `LIMITED` | `9eeb0b00dc46c3caf849d377de994e5a3ba20b0d181360914cf46b54131e1c8f` | 7408 |
| `animus.p5.crt.power` | ANIMUS_P5_CRT_POWER | canonical | `PASS` | `daa13c992968be65b04fe0711dadfc700d9232c6baecc5e9ba5152e395a70d5a` | 996 |
| `animus.p5.crt.psychometric` | ANIMUS_P5_CRT_PSYCHOMETRIC | canonical | `PASS` | `864271ad48f934a991e2397036abff7ad415e7a88bbef88aa78b86c8a4cfea2f` | 788 |
| `animus.p5.crt.recovery` | ANIMUS_P5_CRT_RECOVERY | canonical | `PASS` | `d5976cd23bb3081c69f9f8f01f1becf724472507b35e5f96fdd1b83b1a4c462b` | 7565 |
| `animus.p5.crt.recovery.belief` | ANIMUS_P5_CRT_RECOVERY_BELIEF | canonical | `PASS` | `a2592e714f745b940869c9875162da6ba38b7343d640741f8211742ff7b122c7` | 2531 |
| `animus.p5.crt.sim` | ANIMUS_P5_CRT_SIM | canonical | `LIMITED` | `3b9c89ae29d29fed7b736dfba713cce3bc28b9f3f8c5d0042013847fe172219b` | 5442 |
| `animus.p5.crt.specificity` | ANIMUS_P5_CRT_SPECIFICITY | historical | `PASS` | `e1b39e8bce7a542ab24ef624c593bfc6b0c5bef70cdf1c1908eb3b741f23b072` | 6256 |
| `animus.p5.crt.specificity.belief` | ANIMUS_P5_CRT_SPECIFICITY | canonical | `LIMITED` | `b32d1267a6d12c77602e8ca5b6f8ea942c7843e2d7fd6a682f9936ee20e1c1ea` | 3494 |
| `animus.p5.crt.theory` | ANIMUS_P5_CRT_THEORY | canonical | `PASS` | `7b050806160fafc42cf6f661c23588a678540bd1e2d915479961e1af51b73686` | 2213 |
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
