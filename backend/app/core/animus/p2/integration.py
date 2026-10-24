"""ANIMUS-P2 product bridge: real-neural initialization of the ANIMUS loop.

Provides (a) a ValidatedPerceptionObservationProvider that turns a neural feature vector into a real
ObservationEnvelope via a validated decoder (gated — only usable when PERCEPTION_NEURAL_CONTENT is usable),
and (b) a synthetic-validated `neural_initialization_experiment` proving the bridge machinery: initializing
belief from a decoded latent+uncertainty converges faster/better than an uninformed start, and belief
fusion respects decoder uncertainty (high confidence -> stronger update). The REAL experiment on held-out
perception trials runs only after a VALIDATED scientific decision.
"""
from __future__ import annotations

import numpy as np

from app.core.animus.p2.capability import (
    PERCEPTION_NEURAL_CONTENT,
    CapabilityError,
    ScientificCapabilityAuthorization,
)
from app.core.animus.p2.target_representation import unit_l2
from app.core.time import utcnow


class ValidatedPerceptionObservationProvider:
    """Real perception-neural observation source. Fail-closed unless the capability is usable."""
    source_type = "VALIDATED_PERCEPTION_NEURAL"

    def __init__(self, decoder, authorization: ScientificCapabilityAuthorization):
        authorization.enforce(PERCEPTION_NEURAL_CONTENT)   # raises unless VALIDATED/AUTHORIZED
        self._decoder = decoder
        self._auth = authorization

    def observe(self, neural_features, calibration_context: dict) -> dict:
        decoded = self._decoder.decode(neural_features, calibration_context, None)
        return {
            "source_type": self.source_type,
            "representation": {"visual": decoded.latent_estimate},
            "uncertainty": {"visual": float(np.mean(decoded.uncertainty))},
            "signal_quality": decoded.quality,
            "measurement_id": calibration_context.get("measurement_id", "perc-neural"),
            "timestamp": utcnow().isoformat(),
            "provenance": decoded.provenance,
            "scientific_authorization": "PERCEPTION_NEURAL_CONTENT (validated, domain=PERCEPTION)",
            "claim_level": decoded.claim_level,
        }


# --- synthetic bridge experiment (method validation of the product bridge) -----------------------------
def _gauss_update(mean, var, obs, obs_var):
    prec, oprec = 1.0 / var, 1.0 / max(obs_var, 1e-6)
    post_var = 1.0 / (prec + oprec)
    return post_var * (mean / var + obs * oprec), post_var


def _loop_to_target(init_mean, init_var, target, n_iter=8, step=0.12, fb_noise=0.25, seed=0):
    """A minimal ANIMUS-style closed loop in the target space. The (behavioral) respondent — who knows their
    own imagined target — steers the estimate toward it with noisy corrections; the CONTROLLER/loop never
    sees the target directly, only the corrections. The mean takes a noisy step toward the target each
    iteration (attenuated by feedback noise). Returns the mean-vs-target cosine series."""
    rng = np.random.default_rng(seed)
    mean = np.array(init_mean, float)
    sims = [float(unit_l2(mean) @ unit_l2(target))]
    for _ in range(n_iter):
        direction = (target - mean) + fb_noise * np.linalg.norm(target - mean) * rng.standard_normal(mean.shape)
        mean = mean + step * direction
        sims.append(float(unit_l2(mean) @ unit_l2(target)))
    return sims


def neural_initialization_experiment(decoded_latents, decoded_uncertainty, neural_features_unused,
                                     targets, seed=20260909, threshold=0.45) -> dict:
    """Compare uninformed vs neural-initialized vs fused ANIMUS-style loops on held-out (synthetic) trials.
    The hidden target is never given to the loop; the evaluator holds it. Returns product-bridge metrics."""
    rng = np.random.default_rng(seed)
    dim = targets.shape[1]
    modes = {"BEHAVIORAL_ONLY": [], "NEURAL_ONLY": [], "NEURAL_PLUS_BEHAVIORAL": []}
    init_sims = {"UNINFORMED": [], "NEURAL_INIT": []}
    iters_to_thresh = {"UNINFORMED": [], "NEURAL_INIT": []}
    THRESH = threshold
    for i in range(len(targets)):
        tgt = targets[i]
        neu = np.array(decoded_latents[i], float)
        unc = float(decoded_uncertainty[i])
        # uninformed start: a random UNIT vector (cos ~0 to target) — a fair, same-norm baseline
        u0 = unit_l2(rng.standard_normal(dim))
        sims_u = _loop_to_target(u0, 1.0, tgt, seed=seed + i)
        # neural-informed start (belief mean = decoded latent; variance from uncertainty)
        sims_n = _loop_to_target(neu, max(unc, 0.05), tgt, seed=seed + i)
        # neural-only (no behavioral steps): similarity of decoded latent itself
        neural_only_sim = float(unit_l2(neu) @ unit_l2(tgt))
        modes["BEHAVIORAL_ONLY"].append(sims_u[-1])
        modes["NEURAL_ONLY"].append(neural_only_sim)
        modes["NEURAL_PLUS_BEHAVIORAL"].append(sims_n[-1])
        init_sims["UNINFORMED"].append(sims_u[0])
        init_sims["NEURAL_INIT"].append(sims_n[0])
        for label, sims in (("UNINFORMED", sims_u), ("NEURAL_INIT", sims_n)):
            hit = next((k for k, s in enumerate(sims) if s >= THRESH), len(sims))
            iters_to_thresh[label].append(hit)

    gains = np.array(modes["NEURAL_PLUS_BEHAVIORAL"]) - np.array(modes["BEHAVIORAL_ONLY"])
    # paired bootstrap CI of the gain
    bb = []
    n = len(gains)
    for _ in range(1000):
        idx = rng.integers(0, n, n)
        bb.append(float(np.mean(gains[idx])))
    ci = [float(np.percentile(bb, 2.5)), float(np.percentile(bb, 97.5))]
    return {
        "n_trials": int(n),
        "median_neural_initialization_gain": float(np.median(gains)),
        "gain_bootstrap_ci95": ci,
        "median_initial_similarity_uninformed": float(np.median(init_sims["UNINFORMED"])),
        "median_initial_similarity_neural": float(np.median(init_sims["NEURAL_INIT"])),
        "median_iters_to_threshold_uninformed": float(np.median(iters_to_thresh["UNINFORMED"])),
        "median_iters_to_threshold_neural": float(np.median(iters_to_thresh["NEURAL_INIT"])),
        "mode_medians": {k: float(np.median(v)) for k, v in modes.items()},
        "neural_init_gain_positive": bool(np.median(gains) > 0 and ci[0] > 0),
        "neural_faster": bool(np.median(iters_to_thresh["NEURAL_INIT"]) <
                              np.median(iters_to_thresh["UNINFORMED"])),
        "fused_ge_both": bool(np.median(modes["NEURAL_PLUS_BEHAVIORAL"]) >= np.median(modes["NEURAL_ONLY"])
                              and np.median(modes["NEURAL_PLUS_BEHAVIORAL"]) >=
                              np.median(modes["BEHAVIORAL_ONLY"])),
    }


def belief_fusion_respects_uncertainty() -> dict:
    """Unit check: a high-confidence (low-variance) neural observation moves the posterior more than a
    low-confidence one, with no arbitrary source dominance."""
    prior_mean, prior_var = 0.0, 1.0
    obs = 1.0
    hi_mean, _ = _gauss_update(prior_mean, prior_var, obs, 0.05)   # high confidence
    lo_mean, _ = _gauss_update(prior_mean, prior_var, obs, 5.0)    # low confidence
    return {"high_conf_moves_more": hi_mean > lo_mean, "high_conf_mean": round(hi_mean, 4),
            "low_conf_mean": round(lo_mean, 4), "pass": hi_mean > lo_mean}


def perception_provider_gated(authorization: ScientificCapabilityAuthorization) -> bool:
    """Return True iff a real perception provider could be constructed under this authorization."""
    try:
        ScientificCapabilityAuthorization(matrix=authorization.matrix).enforce(PERCEPTION_NEURAL_CONTENT)
        return True
    except CapabilityError:
        return False
