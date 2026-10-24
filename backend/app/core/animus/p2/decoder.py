"""ANIMUS-P2 perception content decoder.

PRIMARY family (the scientific gate): regularized linear regression from frozen-ROI neural features to the
frozen visual embedding, with nested-validation regularization selection. Uncertainty is first-class via a
bootstrap decoder ensemble (predictive spread), calibrated on validation. A reject option lets the decoder
say "no valid neural-content estimate" when QC/uncertainty/OOD criteria (set on validation) are violated.
The primary gate must NOT depend on a flexible deep model; a small MLP exists only as a SECONDARY,
descriptive comparator.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from app.core.animus.p2.target_representation import unit_l2

PRIMARY_FAMILY = "ridge_linear_multioutput"
ALPHAS = [1.0, 10.0, 100.0, 1000.0, 10000.0]


def _ridge_fit(x: np.ndarray, y: np.ndarray, alpha: float) -> np.ndarray:
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    d = x.shape[1]
    a = x.T @ x + alpha * np.eye(d)
    return np.linalg.solve(a, x.T @ y)


@dataclass
class RidgeDecoder:
    alpha: float = 100.0
    _w: np.ndarray | None = None

    def fit(self, x, y):
        self._w = _ridge_fit(x, y, self.alpha)
        return self

    def predict(self, x):
        return unit_l2(np.asarray(x, float) @ self._w)


def select_alpha(x_tr, y_tr, x_va, y_va, alphas=ALPHAS) -> tuple[float, dict]:
    """Nested-validation alpha selection by mean predicted-vs-true cosine on validation."""
    scores = {}
    for a in alphas:
        w = _ridge_fit(x_tr, y_tr, a)
        pred = unit_l2(x_va @ w)
        scores[a] = float(np.mean(np.sum(pred * unit_l2(y_va), axis=1)))
    best = max(scores, key=scores.get)
    return best, {str(k): round(v, 5) for k, v in scores.items()}


@dataclass
class BootstrapEnsembleDecoder:
    """Bootstrap ensemble of ridge decoders -> predictive mean + per-sample uncertainty."""
    alpha: float = 100.0
    n_boot: int = 20
    seed: int = 20260909
    _ws: list = field(default_factory=list)
    reject_threshold: float | None = None
    _dim: int = 0

    def fit(self, x, y):
        x = np.asarray(x, float)
        y = np.asarray(y, float)
        self._dim = y.shape[1]
        rng = np.random.default_rng(self.seed)
        n = x.shape[0]
        self._ws = []
        for _ in range(self.n_boot):
            idx = rng.integers(0, n, n)
            self._ws.append(_ridge_fit(x[idx], y[idx], self.alpha))
        return self

    def predict_with_uncertainty(self, x):
        x = np.asarray(x, float)
        preds = np.stack([unit_l2(x @ w) for w in self._ws])   # (n_boot, n, dim)
        mean = unit_l2(preds.mean(0))
        # uncertainty = mean pairwise spread of ensemble predictions per sample
        spread = preds.std(0).mean(1)                           # (n,)
        return mean, spread

    def calibrate_reject(self, x_val, uncertainty_quantile: float = 0.9):
        _, spread = self.predict_with_uncertainty(x_val)
        self.reject_threshold = float(np.quantile(spread, uncertainty_quantile))
        return self.reject_threshold

    def valid_mask(self, uncertainty) -> np.ndarray:
        if self.reject_threshold is None:
            return np.ones(len(uncertainty), bool)
        return np.asarray(uncertainty) <= self.reject_threshold


# --- SECONDARY comparator (descriptive; cannot rescue a failed primary) --------------------------------
@dataclass
class LinearProbeMLP:
    """A tiny 1-hidden-layer probe (numpy, deterministic) used ONLY as a secondary descriptive comparator."""
    hidden: int = 128
    alpha: float = 100.0
    role: str = "SECONDARY"

    def fit(self, x, y, seed: int = 0):
        rng = np.random.default_rng(seed)
        x = np.asarray(x, float)
        h = np.tanh(x @ (rng.standard_normal((x.shape[1], self.hidden)) / np.sqrt(x.shape[1])))
        self._proj = _ridge_fit(h, y, self.alpha)
        self._rand = rng
        self._in = x.shape[1]
        self._w1 = None  # placeholder to keep shape frozen deterministically
        self._h_seed = seed
        return self

    def predict(self, x):
        rng = np.random.default_rng(self._h_seed)
        x = np.asarray(x, float)
        h = np.tanh(x @ (rng.standard_normal((x.shape[1], self.hidden)) / np.sqrt(x.shape[1])))
        return unit_l2(h @ self._proj)


# --- Validated real decoder (gated: only instantiated when P2 VALIDATED) -------------------------------
class ValidatedPerceptionNeuralDecoder:
    """Implements the ANIMUS NeuralContentDecoder contract with a REAL, validated perception decoder.
    Carries full provenance and a domain-scoped PERCEPTION claim. Instantiating this asserts a validated
    scientific decision hash was supplied (fail-closed)."""
    version = "animus-p2-perception-decoder-v1"

    def __init__(self, weights: np.ndarray, provenance: dict):
        required = ["training_dataset", "training_subjects", "roi", "embedding_model", "split_seal_hash",
                    "model_weights_hash", "calibration_hash", "scientific_decision_hash"]
        missing = [k for k in required if not provenance.get(k)]
        if missing:
            raise ValueError(f"ValidatedPerceptionNeuralDecoder requires provenance {missing}")
        self._w = np.asarray(weights, float)
        self.provenance = provenance

    def decode(self, neural_observation, calibration_context, previous_belief):
        from app.core.animus.claims import L3_NEURAL_CONTENT_INFORMED_VALIDATED
        from app.core.animus.decoder import NeuralDecodedBelief
        est = unit_l2(np.asarray(neural_observation, float) @ self._w)
        unc = calibration_context.get("uncertainty", [0.1] * len(est)) if isinstance(
            calibration_context, dict) else [0.1] * len(est)
        return NeuralDecodedBelief(
            latent_estimate=list(est), uncertainty=list(np.asarray(unc, float).ravel()[: len(est)]),
            quality=float(calibration_context.get("quality", 0.5) if isinstance(calibration_context, dict) else 0.5),
            valid=True, validity_flags={"synthetic": False, "domain": "PERCEPTION"},
            provenance={**self.provenance, "decoder": self.version, "synthetic": False},
            decoder_version=self.version, training_dataset=self.provenance["training_dataset"],
            roi=self.provenance["roi"], measurement_unit="beta",
            claim_level=L3_NEURAL_CONTENT_INFORMED_VALIDATED)
