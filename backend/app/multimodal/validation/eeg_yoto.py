"""Real-EEG validation on OpenNeuro ds005815 (YOTO: visual/auditory perception and imagery, 30-ch, 1000 Hz).

Trial structure (authors' description, codebook in ``app.research.neural.trigger_codebook``): fixation 2 s ->
stimulus/perception 2 s -> imagery 4 s -> vividness rating. Analyses use visual-only trials (codes 21-23).

Windows (s, relative to the stimulus trigger), equal length so spectral power is comparable:
fixation [-1.5, 0), perception [0.5, 2.0), imagery [3.0, 4.5). The first second of imagery is skipped to avoid the
stimulus-offset evoked response. "Fixation" is pre-stimulus fixation, not resting state.

Leakage controls: the perception and imagery epochs of one trial always fall in the same fold (folds are defined by
recording or subject); cross-session folds never share a recording; LOSO folds never share a subject. Riemannian
re-centering uses only unlabeled covariances of each recording (Zanini et al., 2018), never labels.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.multimodal.evaluation import check_group_leakage, expected_calibration_error
from app.multimodal.validation.gates import Criterion, GateResult

WINDOWS = {"fixation": (-1.5, 0.0), "perception": (0.5, 2.0), "imagery": (3.0, 4.5)}
VISUAL_CODES = {21: "face", 22: "face", 23: "square"}
SFREQ = 250.0
REJECT_PTP_UV = 200.0
BANDS = [(4, 8), (8, 13), (13, 20), (20, 30), (30, 40)]
PSEUDO_SALT = b"imagina-phase2-ds005815"
MIN_TRIALS_PER_RECORDING = 10


def pseudo(sub: str) -> str:
    return "P" + hashlib.sha256(PSEUDO_SALT + sub.encode()).hexdigest()[:6]


@dataclass
class EpochSet:
    x: np.ndarray
    meta: list[dict]
    ch_names: list[str]
    report: dict

    def sel(self, **conds) -> np.ndarray:
        m = np.ones(len(self.meta), dtype=bool)
        for k, v in conds.items():
            vals = np.array([r[k] for r in self.meta])
            m &= np.isin(vals, v if isinstance(v, (list, tuple, set)) else [v])
        return m

    def subset(self, mask: np.ndarray) -> EpochSet:
        return EpochSet(self.x[mask], [m for m, k in zip(self.meta, mask) if k], self.ch_names, self.report)

    def col(self, key: str, mask=None) -> np.ndarray:
        arr = np.array([r[key] for r in self.meta])
        return arr if mask is None else arr[mask]


def build_epochs(root: Path, cache: Path | None = None) -> EpochSet:
    import mne

    from app.research.neural.adapters.yoto import YotoAdapter

    if cache and cache.exists():
        z = np.load(cache, allow_pickle=False)
        return EpochSet(z["x"], json.loads(str(z["meta"])), json.loads(str(z["ch"])), json.loads(str(z["report"])))
    adapter = YotoAdapter(str(root))
    xs, meta, report, ch_ref = [], [], {"recordings": []}, None
    for vhdr in sorted(root.glob("sub-*/ses-*/eeg/*_task-task_eeg.vhdr")):
        sub = vhdr.name.split("_")[0]
        ses = vhdr.name.split("_")[1].split("-")[1]
        entry = {"participant": pseudo(sub), "session": ses}
        try:
            _, trials = adapter.ingest_recording(sub, ses)
            raw = mne.io.read_raw_brainvision(vhdr, preload=True, verbose="error")
            raw.pick("eeg")
            if ch_ref is None:
                ch_ref = list(raw.ch_names)
            if list(raw.ch_names) != ch_ref:
                entry["status"] = "excluded: channel set differs"
                report["recordings"].append(entry)
                continue
            raw.filter(1.0, 40.0, verbose="error")
            raw.set_eeg_reference("average", verbose="error")
            raw.resample(SFREQ, verbose="error")
            data = raw.get_data() * 1e6
            var = np.log(np.var(data, axis=1) + 1e-12)
            z = (var - np.median(var)) / (np.median(np.abs(var - np.median(var))) * 1.4826 + 1e-9)
            bad = [raw.ch_names[i] for i in np.where(np.abs(z) > 5)[0]]
            n_t = int(round(1.5 * SFREQ))
            kept = rej = 0
            per_trial = {}
            for t in trials:
                if t.condition != "perception":
                    continue
                code = int(t.trial_id.rsplit("code", 1)[1])
                if code not in VISUAL_CODES:
                    continue
                per_trial[t.trial_id] = (t.event_onset, code, t.behavioral_target)
            for k, (trial_id, (onset, code, viv)) in enumerate(sorted(per_trial.items(), key=lambda kv: kv[1][0])):
                eps = {}
                for phase, (a, _) in WINDOWS.items():
                    i0 = int(round((onset + a) * SFREQ))
                    if i0 < 0 or i0 + n_t > data.shape[1]:
                        break
                    eps[phase] = data[:, i0:i0 + n_t]
                if len(eps) != 3:
                    continue
                if max(np.ptp(e, axis=1).max() for e in eps.values()) > REJECT_PTP_UV:
                    rej += 1
                    continue
                for phase, e in eps.items():
                    xs.append(e.astype(np.float32))
                    meta.append({"participant": pseudo(sub), "session": ses, "recording": f"{pseudo(sub)}_{ses}",
                                 "trial": f"{pseudo(sub)}_{ses}_{trial_id.split('_t')[-1]}", "phase": phase,
                                 "code": code, "content": VISUAL_CODES[code], "vividness": viv, "trial_index": k})
                kept += 1
            entry.update({"status": "ok", "visual_trials_kept": kept, "rejected_ptp": rej, "bad_channels": bad})
        except Exception as e:  # noqa: BLE001
            entry["status"] = f"error: {type(e).__name__}: {e}"[:300]
        report["recordings"].append(entry)
    es = EpochSet(np.stack(xs), meta, ch_ref or [], report)
    if cache:
        np.savez_compressed(cache, x=es.x, meta=json.dumps(meta), ch=json.dumps(es.ch_names),
                            report=json.dumps(report))
    return es


def bandpower_features(x: np.ndarray) -> np.ndarray:
    from scipy.signal import welch

    f, p = welch(x, fs=SFREQ, nperseg=int(SFREQ), axis=-1)
    return np.concatenate([np.log(p[..., (f >= lo) & (f < hi)].mean(-1) + 1e-12) for lo, hi in BANDS], axis=1)


def covariances(x: np.ndarray) -> np.ndarray:
    from sklearn.covariance import LedoitWolf

    return np.array([LedoitWolf().fit(e.T).covariance_ for e in x.astype(np.float64)])


def _eig_fn(c, fn):
    w, v = np.linalg.eigh(c)
    return (v * fn(np.clip(w, 1e-12, None))) @ v.T


def tangent(covs: np.ndarray, ref: np.ndarray) -> np.ndarray:
    isq = _eig_fn(ref, lambda w: w ** -0.5)
    n = covs.shape[1]
    iu = np.triu_indices(n)
    coef = np.where(iu[0] == iu[1], 1.0, np.sqrt(2.0))
    return np.array([_eig_fn(isq @ c @ isq, np.log)[iu] * coef for c in covs])


def log_euclid_mean(covs: np.ndarray) -> np.ndarray:
    return _eig_fn(np.mean([_eig_fn(c, np.log) for c in covs], axis=0), np.exp)


def recentered_tangent(covs: np.ndarray, units: np.ndarray) -> np.ndarray:
    out = np.empty((covs.shape[0], covs.shape[1] * (covs.shape[1] + 1) // 2))
    for u in np.unique(units):
        m = units == u
        out[m] = tangent(covs[m], log_euclid_mean(covs[m]))
    return out


def _clf():
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    return make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=3000))


def folds(es: EpochSet, mask: np.ndarray, scheme: str):
    rec = es.col("recording", mask)
    part = es.col("participant", mask)
    if scheme == "loso":
        for p in np.unique(part):
            tr, te = np.where(part != p)[0], np.where(part == p)[0]
            check_group_leakage(part[tr], part[te])
            yield tr, te, p
    elif scheme == "cross_session":
        for p in np.unique(part):
            recs = np.unique(rec[part == p])
            if len(recs) < 2:
                continue
            for r in recs:
                tr = np.where((part == p) & (rec != r))[0]
                te = np.where(rec == r)[0]
                check_group_leakage(rec[tr], rec[te])
                yield tr, te, p


def evaluate(es: EpochSet, mask: np.ndarray, y: np.ndarray, feats: dict[str, np.ndarray | None], scheme: str,
             raw_x: np.ndarray | None = None) -> dict:
    from sklearn.metrics import balanced_accuracy_score

    out = {}
    for name, f in feats.items():
        per_part: dict[str, list[float]] = {}
        probs, ys = [], []
        for tr, te, p in folds(es, mask, scheme):
            if len(np.unique(y[tr])) < len(np.unique(y)) or len(np.unique(y[te])) < 2:
                continue
            if f is None:
                m = _model_by_name(name)
                m.fit(raw_x[tr], y[tr])
                pr = m.predict_proba(raw_x[te])
                cls = m.classes_
            else:
                m = _clf().fit(f[tr], y[tr])
                pr = m.predict_proba(f[te])
                cls = m.classes_
            per_part.setdefault(p, []).append(balanced_accuracy_score(y[te], cls[pr.argmax(1)]))
            probs.append(pr)
            ys.append(np.searchsorted(cls, y[te]))
        scores = np.array([np.mean(v) for v in per_part.values()])
        out[name] = {"mean_balanced_accuracy": float(scores.mean()) if scores.size else None,
                     "ci95": _boot(scores), "n_participants": int(scores.size),
                     "per_participant": {k: float(np.mean(v)) for k, v in per_part.items()},
                     "ece": expected_calibration_error(np.vstack(probs), np.concatenate(ys)) if probs else None}
    return out


def _model_by_name(name: str):
    from app.multimodal.processing.eeg_decoding import ShallowNet, make_csp_lda, make_fbcsp_lda

    return {"csp_lda": make_csp_lda, "fbcsp_lda": lambda: make_fbcsp_lda(SFREQ),
            "shallow_net": lambda: ShallowNet(epochs=25)}[name]()


def _boot(v: np.ndarray, n: int = 5000, seed: int = 0) -> list[float] | None:
    if v.size < 2:
        return None
    rng = np.random.default_rng(seed)
    b = [rng.choice(v, v.size).mean() for _ in range(n)]
    return [float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))]


def permutation_test(es: EpochSet, mask: np.ndarray, y: np.ndarray, f: np.ndarray, scheme: str, n_perm: int,
                     observed: float, seed: int = 0) -> dict:
    """Null: phase labels shuffled within each trial (keeps trial and recording structure intact)."""
    rng = np.random.default_rng(seed)
    trials = es.col("trial", mask)
    null = []
    for _ in range(n_perm):
        yp = y.copy()
        for t in np.unique(trials):
            idx = np.where(trials == t)[0]
            yp[idx] = rng.permutation(yp[idx])
        null.append(evaluate(es, mask, yp, {"m": f}, scheme)["m"]["mean_balanced_accuracy"])
    null = np.array(null)
    return {"n_permutations": n_perm, "null_mean": float(null.mean()), "null_p95": float(np.percentile(null, 95)),
            "p_value": float((1 + np.sum(null >= observed)) / (n_perm + 1))}


CRITERIA_A = [
    Criterion("loso_tangent_recentered_bacc_ci_low", ">=", 0.55, 0.50,
              "Perception vs imagery phases differ in visual input, so above-chance decoding is expected; the "
              "lower CI bound must clear chance (0.50) with a margin to count as a working pipeline."),
    Criterion("permutation_p", "<=", 0.01, 0.05, "Trial-preserving label permutation null."),
    Criterion("negative_control_abs_dev_from_chance", "<=", 0.05, 0.10,
              "Random labels on fixation epochs must stay at chance; larger deviations indicate leakage."),
]
CRITERIA_CONTENT = [
    Criterion("imagery_content_cross_session_bacc_ci_low", ">=", 0.52, 0.48,
              "Imagery content (face vs square) is a weak signal in EEG; a CI lower bound above 0.52 is required "
              "to claim decodability; a bound below 0.48 with mean near 0.5 is a null result."),
]


def apply_exclusions(es: EpochSet) -> tuple[EpochSet, dict]:
    """Exclusion rule (declared after artifact rejection counts were known, before any decoding was run):
    a recording needs >= MIN_TRIALS_PER_RECORDING clean visual trials."""
    rec = es.col("recording")
    trials = es.col("trial")
    n = {r: len(np.unique(trials[rec == r])) for r in np.unique(rec)}
    keep = {r for r, k in n.items() if k >= MIN_TRIALS_PER_RECORDING}
    return es.subset(np.isin(rec, list(keep))), {"rule": f">= {MIN_TRIALS_PER_RECORDING} clean visual trials",
                                                 "excluded": {r: k for r, k in n.items() if r not in keep},
                                                 "kept_recordings": len(keep)}


def run_protocols(es: EpochSet, n_perm: int = 100, include_slow: bool = True) -> dict:
    phases = es.col("phase")
    rec = es.col("recording")
    covs = covariances(es.x)
    ts_plain = tangent(covs, log_euclid_mean(covs))
    ts_rc = recentered_tangent(covs, rec)
    bp = bandpower_features(es.x)
    bp_z = bp.copy()
    for r in np.unique(rec):
        m = rec == r
        bp_z[m] = (bp[m] - bp[m].mean(0)) / (bp[m].std(0) + 1e-9)
    results = {}

    m = np.isin(phases, ["perception", "imagery"])
    y = phases[m]
    feats = {"bandpower": bp[m], "bandpower_recording_z": bp_z[m], "tangent_space": ts_plain[m],
             "tangent_space_recentered": ts_rc[m]}
    slow = {"csp_lda": None, "fbcsp_lda": None, "shallow_net": None} if include_slow else {}
    results["A_perception_vs_imagery"] = {s: evaluate(es, m, y, {**feats, **slow}, s, raw_x=es.x[m])
                                         for s in ("cross_session", "loso")}
    obs = results["A_perception_vs_imagery"]["loso"]["tangent_space_recentered"]["mean_balanced_accuracy"]
    results["A_permutation"] = permutation_test(es, m, y, ts_rc[m], "loso", n_perm, obs)
    try:
        from pyriemann.tangentspace import TangentSpace

        ref_ts = TangentSpace(metric="logeuclid").fit_transform(covs[m])
        results["A_pyriemann_reference"] = evaluate(es, m, y, {"pyriemann_tangent_space": ref_ts}, "loso")
    except Exception as e:  # noqa: BLE001
        results["A_pyriemann_reference"] = {"error": repr(e)[:200]}

    m3 = np.ones(len(phases), dtype=bool)
    results["A3_fixation_perception_imagery"] = {
        s: evaluate(es, m3, phases, {"bandpower_recording_z": bp_z, "tangent_space_recentered": ts_rc}, s)
        for s in ("cross_session", "loso")}

    mf = phases == "fixation"
    rng = np.random.default_rng(1)
    trials = es.col("trial", mf)
    fake = np.where(rng.random(len(np.unique(trials))) < 0.5, "a", "b")
    y_fake = fake[np.unique(trials, return_inverse=True)[1]]
    results["negative_control_random_labels_fixation"] = {
        s: evaluate(es, mf, y_fake, {"tangent_space_recentered": ts_rc[mf], "bandpower_recording_z": bp_z[mf]}, s)
        for s in ("cross_session", "loso")}

    for phase in ("imagery", "perception"):
        mc = phases == phase
        yc = es.col("content", mc)
        results[f"content_face_vs_square_{phase}"] = {
            s: evaluate(es, mc, yc, {"bandpower_recording_z": bp_z[mc], "tangent_space_recentered": ts_rc[mc]}, s)
            for s in ("cross_session", "loso")}
    return results


def gate_protocol_a(es: EpochSet, res: dict, dataset: dict) -> GateResult:
    a = res["A_perception_vs_imagery"]
    neg = res["negative_control_random_labels_fixation"]
    neg_dev = max(abs(v["mean_balanced_accuracy"] - 0.5) for s in neg.values() for v in s.values()
                  if v["mean_balanced_accuracy"] is not None)
    rc = a["loso"]["tangent_space_recentered"]
    g = GateResult(
        experiment="EEG_PROTOCOL_A_PERCEPTION_VS_IMAGERY_DS005815",
        dataset=dataset,
        participants={"n_participants": len({r["participant"] for r in es.meta}),
                      "n_recordings": len({r["recording"] for r in es.meta}),
                      "recordings": es.report["recordings"]},
        task_and_labels=("Visual trials (face/square). Labels = trial phase: perception (stimulus on screen) vs "
                         "imagery (blank screen, instructed visualization). Perception includes visual input, so "
                         "this contrast is not evidence of decoding imagery content."),
        design="Within-subject cross-session (train one session, test the other) and leave-one-subject-out.",
        metric_definitions={"balanced_accuracy": "per-participant mean over folds, then averaged; CI = bootstrap "
                                                 "over participants", "ece": "10-bin expected calibration error"},
        criteria=CRITERIA_A,
        results=res,
        baseline={"chance": 0.5, "bandpower_loso": a["loso"]["bandpower"]["mean_balanced_accuracy"]},
        leakage_checks={"fold_unit": "recording (cross-session) / participant (LOSO); asserted in code",
                        "trial_pairing": "both phases of a trial always in the same fold",
                        "recentering": "unsupervised, per recording, label-free"},
        negative_controls={"random_labels_fixation_max_abs_dev": neg_dev, "permutation": res["A_permutation"]},
        generalization={"recentering_gain_loso": rc["mean_balanced_accuracy"] -
                        a["loso"]["tangent_space"]["mean_balanced_accuracy"]},
        limitations=["Perception and imagery windows differ in time-since-trial-onset and in visual input; "
                     "decodability does not show imagery-specific neural content.",
                     "No ocular artifact removal beyond amplitude rejection; eye movements may contribute.",
                     "Pre-stimulus fixation is not a resting state."],
    )
    g.decide({"loso_tangent_recentered_bacc_ci_low": (rc["ci95"] or [None])[0],
              "permutation_p": res["A_permutation"]["p_value"],
              "negative_control_abs_dev_from_chance": neg_dev})
    return g


def gate_content(es: EpochSet, res: dict, dataset: dict) -> GateResult:
    ci = res["content_face_vs_square_imagery"]["cross_session"]["tangent_space_recentered"]
    g = GateResult(
        experiment="EEG_IMAGERY_CONTENT_FACE_VS_SQUARE_DS005815",
        dataset=dataset, participants={"n_participants": ci["n_participants"]},
        task_and_labels="Imagery phase only: imagined face (codes 21/22) vs imagined square (code 23).",
        design="Within-subject cross-session; LOSO reported as secondary. Perception-phase content reported for "
               "comparison.",
        metric_definitions={"balanced_accuracy": "as protocol A"},
        criteria=CRITERIA_CONTENT,
        results={k: v for k, v in res.items() if k.startswith("content_")},
        baseline={"chance": 0.5},
        leakage_checks={"fold_unit": "recording"},
        limitations=["Two coarse content classes; stimulus counts unbalanced (2:1) — balanced accuracy used.",
                     "A null here does not show absence of imagery content, only that these features do not "
                     "recover it reliably."],
    )
    g.decide({"imagery_content_cross_session_bacc_ci_low": (ci["ci95"] or [None])[0]})
    return g


def vividness_analysis(es: EpochSet) -> GateResult:
    """Protocol B: does imagery-window EEG add to a behavioral baseline for predicting high (5) vs lower (<5)
    vividness? Within-subject cross-session AUC; participants need >= 10 trials in each class per session."""
    from sklearn.metrics import roc_auc_score

    m = (es.col("phase") == "imagery") & np.array([r["vividness"] is not None for r in es.meta])
    viv = es.col("vividness", m).astype(float)
    y = (viv >= 5).astype(int)
    part, rec = es.col("participant", m), es.col("recording", m)
    ok_parts = [p for p in np.unique(part)
                if all(min(np.sum(y[rec == r] == 1), np.sum(y[rec == r] == 0)) >= 10 for r in np.unique(rec[part == p]))
                and len(np.unique(rec[part == p])) == 2]
    content = (es.col("content", m) == "face").astype(float)
    tidx = es.col("trial_index", m).astype(float)
    sess = (es.col("session", m) == "2").astype(float)
    prev = np.zeros_like(viv)
    for r in np.unique(rec):
        idx = np.where(rec == r)[0]
        order = idx[np.argsort(tidx[idx])]
        prev[order[1:]] = viv[order[:-1]]
        prev[order[0]] = np.median(viv[idx])
    behav = np.column_stack([content, tidx / 50.0, sess, prev])
    covs = covariances(es.x[m])
    neural = np.hstack([recentered_tangent(covs, rec), bandpower_features(es.x[m])])
    aucs = {"behavioral": [], "neural": [], "behavioral+neural": []}
    for p in ok_parts:
        for r in np.unique(rec[part == p]):
            tr = (part == p) & (rec != r)
            te = rec == r
            for name, f in (("behavioral", behav), ("neural", neural), ("behavioral+neural", np.hstack([behav,
                                                                                                         neural]))):
                mdl = _clf().fit(f[tr], y[tr])
                aucs[name].append((p, roc_auc_score(y[te], mdl.predict_proba(f[te])[:, 1])))
    per = {k: {p: float(np.mean([a for q, a in v if q == p])) for p in ok_parts} for k, v in aucs.items()}
    delta = np.array([per["behavioral+neural"][p] - per["behavioral"][p] for p in ok_parts])
    g = GateResult(
        experiment="EEG_PROTOCOL_B_VIVIDNESS_DS005815",
        dataset={"name": "OpenNeuro ds005815", "labels": "Trigger_Vividness_Data.csv (1-5 self-report)"},
        participants={"n_eligible": len(ok_parts), "eligibility": ">=10 trials rated 5 and >=10 rated <5 in each "
                                                                  "session"},
        task_and_labels="Imagery-window EEG, visual trials; label = vividness 5 vs <5 (ceiling-skewed scale).",
        design="Within-subject cross-session; behavioral baseline = content, trial index, session, previous rating.",
        metric_definitions={"auc": "ROC AUC per held-out session, averaged per participant",
                            "delta_auc": "(behavioral+neural) - behavioral, per participant; bootstrap CI"},
        criteria=[Criterion("delta_auc_ci_low", ">=", 0.0, -0.05,
                            "Neural features must add to the behavioral baseline; prior repository gate C1 found a "
                            "significant negative increment on this dataset with different features.")],
        results={"per_participant_auc": per,
                 "mean_auc": {k: float(np.mean(list(v.values()))) if v else None for k, v in per.items()},
                 "delta_auc_mean": float(delta.mean()) if delta.size else None, "delta_auc_ci95": _boot(delta)},
        baseline={"behavioral_auc": float(np.mean(list(per["behavioral"].values()))) if ok_parts else None},
        leakage_checks={"fold_unit": "recording; previous-rating feature uses only earlier trials of the same "
                                     "session"},
        limitations=["Vividness ratings are ceiling-skewed (58% are 5/5), leaving few eligible participants.",
                     "Self-report vividness is the only direct measure; this tests prediction, not validity of the "
                     "self-report itself."],
    )
    if not ok_parts:
        g.blocked_reason = "no participant meets the class-balance eligibility rule"
    g.decide({"delta_auc_ci_low": (g.results.get("delta_auc_ci95") or [None])[0]})
    return g
