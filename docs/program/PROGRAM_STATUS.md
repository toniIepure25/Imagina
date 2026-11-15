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
| ANIMUS_P5_CRT_PROTOCOL_INTEGRITY | Counterfactual Reality Testing Stage 0F protocol integrity | `PASS` | `animus.p5.crt.protocol_audit` | Design-integrity gate for the Stage 0F protocol. A PASS requires consistent trial arithmetic, a yoked primary prediction contrast, a labelled active package contrast, six tests, the fluency trap, and a session duration within the 75-minute cap. It does not authorize human collection. |
| ANIMUS_P5_CRT_DESIGN_POWER | Counterfactual Reality Testing Stage 0F design power | `LIMITED` | `animus.p5.crt.design_power` | Simulation-only planning gate. A PASS requires at least 90% power for the stated smallest effect of interest, 80% for the false-seen distortion assay, and 80% for the reliability lower bound. A REVIEW means the current N/trial design is not adequately powered and must not be registered as confirmatory. |
| ANIMUS_P5_CRT_DISTORTION_ASSAY | Counterfactual Reality Testing Stage 0F distortion assay | `PASS` | `animus.p5.crt.distortion` | Simulation-only assay-validation gate. A PASS means the paired false-seen assay detects an injected 5-percentage-point shift with at least 80% power while the b_pi=0 readout-only model remains null. A separate b_pi>0 run illustrates a model-predicted bias channel. It does not show that dual prediction causes distortion in humans. |
| ANIMUS_P5_CRT_HIERARCHICAL_SCREENING | Counterfactual Reality Testing Stage 0F hierarchical recovery screening | `PASS` | `animus.p5.crt.hierarchical_screening` | Conditional group-mean screening with participant-level pi variation. A PASS is screening evidence only; it is not joint hierarchical SBC and does not recover M3/M4. The endpoint-level hierarchical SBC is reported separately; the trial-level CRT model remains outstanding. |
| ANIMUS_P5_CRT_HIERARCHICAL_SBC | Counterfactual Reality Testing Stage 0F endpoint hierarchical SBC | `PASS` | `animus.p5.crt.hierarchical_sbc` | Full hierarchical Bayes for the Stage 1D paired false-seen endpoint (group means, between-person SD, participant-level differences, known binomial SEs), with 1,000 prior draws. A PASS means the endpoint rank histogram is calibrated and 95% coverage is in range. It is not a trial-level CRT source-monitoring SBC. |
| ANIMUS_P5_CRT_MODEL_RECOVERY_DUAL | Counterfactual Reality Testing Stage 0F endpoint model recovery | `PASS` | `animus.p5.crt.model_recovery` | Hierarchical endpoint recovery among four parameterizations: no format effect (M0), common format effect (M2), dual-specific effect (M3), and dual plus nondiagnostic-demand effect (M4). A PASS requires balanced accuracy >=0.85. These are endpoint models, not the Stage 0D theory models. |
| ANIMUS_P5_CRT_STAGE0G_DESIGN_POWER | Counterfactual Reality Testing Stage 0G design power | `PASS` | `animus.p5.crt.stage0g_design_power` | Planning approximation at N=480 and d=0.20. A PASS requires at least 90% power for the primary yoked contrast. It is not trial-level model power and is not human evidence. |
| ANIMUS_P5_CRT_TRIAL_SBC | Counterfactual Reality Testing Stage 0G trial-level SBC | `PASS` | `animus.p5.crt.trial_sbc` | Trial-level hierarchical readout SBC with participant random effects and condition effects. A PASS means the target condition-effect ranks/coverage are calibrated for the readout model. It is not the full CRT source-monitoring POMDP and does not authorize human collection. |
| ANIMUS_P5_CRT_TRIAL_RECOVERY | Counterfactual Reality Testing Stage 0G trial-level model recovery | `LIMITED` | `animus.p5.crt.trial_recovery` | BIC-based effect-conditioned recovery among the confirmatory M0/M2/M4 readout models; M1/M3/M5 are exploratory. A PASS requires balanced accuracy >=0.85. It validates the readout model family, not the full CRT theory tournament. |
| ANIMUS_P5_CRT_STAGE0H_MODEL_SPACE | Counterfactual Reality Testing Stage 0H model space | `PASS` | `animus.p5.crt.stage0h_model_space` | Declares M0-M7 and the confirmatory M0/M2/M4/M6/M7 set. A PASS means the model space and exploratory labels are explicit; it is not evidence for any model. |
| ANIMUS_P5_CRT_STAGE0H_DESIGN_OPTIMIZATION | Counterfactual Reality Testing Stage 0H design optimization | `LIMITED` | `animus.p5.crt.stage0h_design_optimization` | Offline screening of trial compositions for model discrimination under a power floor. A PASS means a candidate reaches the discrimination and power thresholds; it is not human evidence and the classifier used to rank candidates is not a hypothesis test. |
| ANIMUS_P5_CRT_STAGE0H_FULL_MODEL_SBC | Counterfactual Reality Testing Stage 0H full-model SBC | `LIMITED` | `animus.p5.crt.stage0h_full_model_sbc` | Full joint latent-source SBC with observed test choice. A PASS means the declared target parameters are calibrated for this likelihood; it is not the policy POMDP or human evidence. |
| ANIMUS_P5_CRT_STAGE0H_FULL_MODEL_RECOVERY | Counterfactual Reality Testing Stage 0H full-model recovery | `LIMITED` | `animus.p5.crt.stage0h_full_model_recovery` | BIC recovery among the pre-specified full joint models. A PASS requires balanced accuracy >=0.85 under the recorded simulation conditions; it is identifiability evidence only. |
| ANIMUS_P5_CRT_STAGE0H_READINESS | Counterfactual Reality Testing Stage 0H readiness | `BLOCKED` | `animus.p5.crt.stage0h_package` | Documentation-quality gate. BLOCKED is expected until computational gates, adversarial review, calibration, registration, and ethics are complete. It never authorizes human collection. |
| ANIMUS_P5_CRT_STAGE0I_SOURCE_INTEGRITY | Counterfactual Reality Testing Stage 0I source integrity | `PASS` | `animus.p5.crt.stage0i_source_integrity` | Source metadata and correction audit. A PASS means the cited DOI/PMID records and the Corcoran role correction were checked; it is not a systematic review. |
| ANIMUS_P5_CRT_STAGE0I_INFERENCE_BACKEND | Counterfactual Reality Testing Stage 0I inference backend | `BLOCKED` | `animus.p5.crt.stage0i_inference_backend` | Optional NumPyro/JAX readiness. BLOCKED means confirmatory posterior inference is not installed; Laplace remains approximate and cannot pass a confirmatory gate. |
| ANIMUS_P5_CRT_STAGE0I_IDENTIFIABILITY | Counterfactual Reality Testing Stage 0I identifiability | `LIMITED` | `animus.p5.crt.stage0i_identifiability` | Simulation-only pairwise full-model recovery. A PASS requires all confirmatory models and lower uncertainty bounds above threshold; it is not human evidence. |
| ANIMUS_P5_CRT_STAGE0I_DESIGN_ADO | Counterfactual Reality Testing Stage 0I design optimization | `LIMITED` | `animus.p5.crt.stage0i_design_ado` | Full-joint-model design screen. A PASS requires the complete confirmatory set and minimum pairwise recovery above threshold; it is design evidence, not a hypothesis test. |
| ANIMUS_P5_CRT_STAGE0I_TARGET_DESIGN_READOUT | Counterfactual Reality Testing Stage 0I target readout design | `LIMITED` | `animus.p5.crt.stage0i_target_design_readout` | N=432/T=240 single-replicate hierarchical readout screen with the combined manipulation. It is not a full joint-model fit, SBC, or human evidence, so both PASS and REVIEW map to LIMITED. |
| ANIMUS_P5_CRT_STAGE0I_TARGET_DESIGN_PROJECTION | Counterfactual Reality Testing Stage 0I target design projection | `LIMITED` | `animus.p5.crt.stage0i_target_design_projection` | Pilot full-model BIC separation projected to N=432/T=240 by a normal approximation. It is a planning projection, not a target-scale fit, target-scale SBC, or human evidence. |
| ANIMUS_P5_CRT_STAGE0I_POLICY_SBC | Counterfactual Reality Testing Stage 0I policy calibration | `LIMITED` | `animus.p5.crt.stage0i_policy_sbc` | Discrete policy-model calibration, not continuous-parameter SBC. It does not show that humans use the policy. |
| ANIMUS_P5_CRT_STAGE0I_POLICY_PARAMETER_SBC | Counterfactual Reality Testing Stage 0I policy parameter SBC | `LIMITED` | `animus.p5.crt.stage0i_policy_parameter_sbc` | Laplace approximate SBC for meta-EIG policy parameters. It is not NUTS and does not establish that participants use the policy. |
| ANIMUS_P5_CRT_STAGE0I_FULL_MODEL_SBC | Counterfactual Reality Testing Stage 0I full-model SBC | `LIMITED` | `animus.p5.crt.stage0i_full_model_sbc` | Laplace SBC for all confirmatory latent-source models. A PASS is screening calibration, not NUTS. |
| ANIMUS_P5_CRT_STAGE0I_FULL_MODEL_RECOVERY | Counterfactual Reality Testing Stage 0I full-model recovery | `LIMITED` | `animus.p5.crt.stage0i_full_model_recovery` | BIC recovery across all confirmatory latent-source models. A PASS is simulation identifiability, not human evidence. |
| ANIMUS_P5_CRT_STAGE0I_POLICY_RECOVERY | Counterfactual Reality Testing Stage 0I policy recovery | `LIMITED` | `animus.p5.crt.stage0i_policy_recovery` | Policy-choice recovery in simulation. A PASS is policy identifiability, not human evidence. |
| ANIMUS_P5_CRT_STAGE0I_READINESS | Counterfactual Reality Testing Stage 0I readiness | `BLOCKED` | `animus.p5.crt.stage0i_package` | Documentation-quality readiness gate. BLOCKED is expected until computational gates, independent review, adversarial agreement, calibration, registration, and ethics are complete. |
| ANIMUS_P5_CRT_REGISTRATION_READY | Counterfactual Reality Testing registration readiness | `BLOCKED` | `animus.p5.crt.registration_package` | Documentation-quality gate. READY_FOR_INDEPENDENT_REVIEW means the Stage 0F package is complete enough for PI, statistician, adversarial, and ethics review; it does not authorize human data collection or upgrade any claim. BLOCKED means at least one prerequisite is missing. Endpoint SBC is complete and a trial-level readout SBC is reported, but trial-level readout recovery is a post hoc conditional pass (LIMITED), not a pre-specified full-set pass; the full CRT POMDP SBC, calibration, model-based power, independent review, and ethics remain blockers. |

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
| `animus.p3.power` | ANIMUS_P3_POWER | canonical | `PASS` | `3e73959027a8e61945c9e8e1489aaf8cfd47bb8ece57f4f154bba9b52771d9d5` | 957 |
| `animus.p3.sim` | ANIMUS_P3_SIM | canonical | `PASS` | `a09df32a47f91ff2c5ec1b0fa34e8ecd55cf10c77b9811e9a0d363b096ecb6f7` | 1851 |
| `animus.p4.art.power` | ANIMUS_P4_ART_POWER | canonical | `PASS` | `359f61f26e168483463ebb7a0fadb01f8d1ef3b7480682501f9944f6c72ad4a1` | 957 |
| `animus.p4.art.recovery` | ANIMUS_P4_ART_RECOVERY | canonical | `PASS` | `b234f87ad7537c10946c78a9179855d6eea5ea5ad42e65c21572cab6f3743e0d` | 5794 |
| `animus.p4.art.sim` | ANIMUS_P4_ART_SIM | canonical | `PASS` | `7f4f07d3d0a368a879042e62930108f4d8e2f92114b9773e753cce4b0c5ed2c6` | 1527 |
| `animus.p5.crt.calibration` | ANIMUS_P5_CRT_CALIBRATION | canonical | `PASS` | `a022df077fc294e9bc72a9e65b90419fe486c963744b852378a4deae02b8986e` | 3220 |
| `animus.p5.crt.counterfactual` | ANIMUS_P5_CRT_COUNTERFACTUAL | canonical | `LIMITED` | `7adbda8266213500b6e7725e0b983eacef87d96dd9de3b5f462dfda48ab422a1` | 3771 |
| `animus.p5.crt.design_power` | ANIMUS_P5_CRT_DESIGN_POWER | canonical | `LIMITED` | `d9e8f570a7ff9597461bf8c6fe43526177660101d6295fc6848386daa58a5a5e` | 30746 |
| `animus.p5.crt.distortion` | ANIMUS_P5_CRT_DISTORTION_ASSAY | canonical | `PASS` | `134095a50b8095743ff0de6ff15e1feac0e8b475781d77b1425ab186e4e12932` | 2146 |
| `animus.p5.crt.gtheory` | ANIMUS_P5_CRT_GTHEORY | canonical | `PASS` | `56bb49fe9ed884ffdd57980679c3f87a71e762bb778ba5833553c7eea3d74ee4` | 1860 |
| `animus.p5.crt.hierarchical_sbc` | ANIMUS_P5_CRT_HIERARCHICAL_SBC | canonical | `PASS` | `d71f6b53fc62c9eedda4d2c0696c8e1396e686cc25e1b73931e823e1ea34d40b` | 1898 |
| `animus.p5.crt.hierarchical_screening` | ANIMUS_P5_CRT_HIERARCHICAL_SCREENING | canonical | `PASS` | `0c413c68decffb2699c5e09bdef46d09d880bc662f064750e2a662c666573aa5` | 891 |
| `animus.p5.crt.model_recovery` | ANIMUS_P5_CRT_MODEL_RECOVERY_DUAL | canonical | `PASS` | `d6e35ff83b8bc678f8f9e9e979cf7138c35b60fa590c8fdb621d50ccdb034e6f` | 1297 |
| `animus.p5.crt.model_repair` | ANIMUS_P5_CRT_MODEL_REPAIR | canonical | `PASS` | `cfb3e0da9269143d19007f7e1b9da5664a401686bd5597cab04ddefdcc7e769a` | 2588 |
| `animus.p5.crt.policy` | ANIMUS_P5_CRT_POLICY | canonical | `LIMITED` | `a855d11a8a45eebf2fb8f01a206cd823d8e50f855ba4f1a6ea7d439fcaf4c686` | 7142 |
| `animus.p5.crt.power` | ANIMUS_P5_CRT_POWER | canonical | `PASS` | `c3bfcf7017382d61d118d099dc1c7203be950006f40ff14a96da0f245571dd24` | 957 |
| `animus.p5.crt.protocol_audit` | ANIMUS_P5_CRT_PROTOCOL_INTEGRITY | canonical | `PASS` | `7449c03fccc023d68072eed03936288d921cddc5899a5ba4c1b5a1f666b6a36a` | 1458 |
| `animus.p5.crt.psychometric` | ANIMUS_P5_CRT_PSYCHOMETRIC | canonical | `PASS` | `4fade52fba03e8852c909b9113925185e9610e94b3ade597bfd05ae6ba3b81f5` | 763 |
| `animus.p5.crt.recovery` | ANIMUS_P5_CRT_RECOVERY | canonical | `PASS` | `376c8152a28581cb8606310161cc46ff38218e927beb7ded750dd9b3cb9d8e69` | 7297 |
| `animus.p5.crt.recovery.belief` | ANIMUS_P5_CRT_RECOVERY_BELIEF | canonical | `PASS` | `ee17d5007ac52ebda7830cc7a49b015f5e7f0c8d536372bb4f566689f13d35f6` | 2397 |
| `animus.p5.crt.registration_package` | ANIMUS_P5_CRT_REGISTRATION_READY | canonical | `BLOCKED` | `ee9fb4c9fa13a042831ee02b2a675309230191c1d269d90e5e5ad1cd8c74b06b` | 1117 |
| `animus.p5.crt.sim` | ANIMUS_P5_CRT_SIM | canonical | `LIMITED` | `e010bba919b9d51516e41146df885293e4159f33e524ba9dfedbcb8b482776a5` | 5253 |
| `animus.p5.crt.specificity` | ANIMUS_P5_CRT_SPECIFICITY | historical | `PASS` | `fa859c3c333008be08e01356a2a3e59c05a569e0d5cf3f43a53ee5c8ea6a4161` | 6054 |
| `animus.p5.crt.specificity.belief` | ANIMUS_P5_CRT_SPECIFICITY | canonical | `LIMITED` | `09b0f8c823afe49a9bd1cae77c7774064a3a85a9884c21f05c7f11db457ecbbd` | 3391 |
| `animus.p5.crt.stage0g_design_power` | ANIMUS_P5_CRT_STAGE0G_DESIGN_POWER | canonical | `PASS` | `a978f0c62b998da2035a28be537a113dfd24d6355641425bea4d47b4b0fc4723` | 1145 |
| `animus.p5.crt.stage0h_design_optimization` | ANIMUS_P5_CRT_STAGE0H_DESIGN_OPTIMIZATION | canonical | `LIMITED` | `4280d4e8880b9473faf5055046466440ba016f67f5f535c19da34931ecb90d7a` | 10552 |
| `animus.p5.crt.stage0h_full_model_recovery` | ANIMUS_P5_CRT_STAGE0H_FULL_MODEL_RECOVERY | canonical | `LIMITED` | `ffbbe2dedea0dbeedd50c24590464aa7329234798e13124b16d28160fc5fc741` | 1034 |
| `animus.p5.crt.stage0h_full_model_sbc` | ANIMUS_P5_CRT_STAGE0H_FULL_MODEL_SBC | canonical | `LIMITED` | `829c1089f270eed627c43a4504b560070947cef29ffb2fc9fb4ab26e33a48bca` | 837 |
| `animus.p5.crt.stage0h_model_space` | ANIMUS_P5_CRT_STAGE0H_MODEL_SPACE | canonical | `PASS` | `9fe4d489ab93eae146d76a413e8f0da9c91c8b2e34894199ab0842663c2c2be5` | 3946 |
| `animus.p5.crt.stage0h_package` | ANIMUS_P5_CRT_STAGE0H_READINESS | canonical | `BLOCKED` | `7f91c6c0e658cabb69a19be5ab84661c94e511bf7b4f8118f14e845d9c2c55b7` | 743 |
| `animus.p5.crt.stage0i_design_ado` | ANIMUS_P5_CRT_STAGE0I_DESIGN_ADO | canonical | `LIMITED` | `286da2f0e9f1be025f05d01e6b33c0cfcb2ca3d0b0234f737600994a6d150fe4` | 3355 |
| `animus.p5.crt.stage0i_full_model_recovery` | ANIMUS_P5_CRT_STAGE0I_FULL_MODEL_RECOVERY | canonical | `LIMITED` | `e94d8a1b885f9b6eabaf1fb8472a34ad4e349e1fc4960f4596946e39791e0a6c` | 1033 |
| `animus.p5.crt.stage0i_full_model_sbc` | ANIMUS_P5_CRT_STAGE0I_FULL_MODEL_SBC | canonical | `LIMITED` | `4c1f7510e4c8b268217883146b8362f6ce9be9b40653b9d458cecb1dcceb1e59` | 5772 |
| `animus.p5.crt.stage0i_identifiability` | ANIMUS_P5_CRT_STAGE0I_IDENTIFIABILITY | canonical | `LIMITED` | `991b4d9438154b73f68ffaa42c0d56df0480afa3c27ffe7439c9d132921ec1b2` | 3445 |
| `animus.p5.crt.stage0i_inference_backend` | ANIMUS_P5_CRT_STAGE0I_INFERENCE_BACKEND | canonical | `BLOCKED` | `2a9b09b47ee46bd36565205fbbfd788c09d003e69aecaa53d8656b49f770605f` | 872 |
| `animus.p5.crt.stage0i_package` | ANIMUS_P5_CRT_STAGE0I_READINESS | canonical | `BLOCKED` | `2ab0f1b219045cc996fe1fb5a2e1324ebb5e881b03e3e70c9031e037c681a220` | 1651 |
| `animus.p5.crt.stage0i_policy_parameter_sbc` | ANIMUS_P5_CRT_STAGE0I_POLICY_PARAMETER_SBC | canonical | `LIMITED` | `d45268d83426696e351a6a6f4329c6f69186d69e64e21012661db70f4f249975` | 1355 |
| `animus.p5.crt.stage0i_policy_recovery` | ANIMUS_P5_CRT_STAGE0I_POLICY_RECOVERY | canonical | `LIMITED` | `9149afb78b953a3ed273651abac693d95ffad7d669efadfce3c1ce3e7c414ccb` | 1393 |
| `animus.p5.crt.stage0i_policy_sbc` | ANIMUS_P5_CRT_STAGE0I_POLICY_SBC | canonical | `LIMITED` | `c821afbca700f1a89c6236cbb6aa537c6a4cbd577aecab26286c70097b703d46` | 805 |
| `animus.p5.crt.stage0i_source_integrity` | ANIMUS_P5_CRT_STAGE0I_SOURCE_INTEGRITY | canonical | `PASS` | `105adf9fff317ad04f636f78dbed3f8cd3f294c8fcb94618d2a95a6a9e91f2db` | 3912 |
| `animus.p5.crt.stage0i_target_design_projection` | ANIMUS_P5_CRT_STAGE0I_TARGET_DESIGN_PROJECTION | canonical | `LIMITED` | `6360c3bf4f9fc68bd284a73c39165307957892d51b84e4fbc0ba2ac83ff1074d` | 9429 |
| `animus.p5.crt.stage0i_target_design_readout` | ANIMUS_P5_CRT_STAGE0I_TARGET_DESIGN_READOUT | canonical | `LIMITED` | `7ead95dd9ff941ce3ef539f638f42119c48ab8fc6256e090e3bf1bbd0dd82d15` | 4160 |
| `animus.p5.crt.theory` | ANIMUS_P5_CRT_THEORY | canonical | `PASS` | `5095c62851e41925dc0c2306eed8923fc6b6c61023ca33ef1a088a093cfbf441` | 2112 |
| `animus.p5.crt.trial_recovery` | ANIMUS_P5_CRT_TRIAL_RECOVERY | canonical | `LIMITED` | `fe39185e9b5ef1b37898b98f387d68b283f27802bb75fe0748137f3268dca266` | 1191 |
| `animus.p5.crt.trial_sbc` | ANIMUS_P5_CRT_TRIAL_SBC | canonical | `PASS` | `1e4bb3314390c9bda2cb5264e933a198be3558146de73722d9e515180386c2a8` | 965 |
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
