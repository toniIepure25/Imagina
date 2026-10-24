"""Signal-detection and reliability helpers for the Scene Threshold instrument.

The functions here are deliberately dependency-free and deterministic. They describe a behavioural
2-AFC task: the participant sees two scenes and chooses the one that matches the encoded scene. The
target side is counterbalanced, so ``criterion`` is not identified; the public bias readout is a signed
side bias, not a yes/no criterion. Thresholds are returned in normalized scene-difference units and are
not comparable across scenes.
"""
from __future__ import annotations

import math
import random
import statistics
from typing import Any, Iterable, Mapping, Sequence

SDT_SCORING_VERSION = "sdt-v1"
DEFAULT_LAPSE = 0.02
MIN_THRESHOLD_TRIALS = 6
MIN_AUC_CLASS = 3
DEFAULT_BOOTSTRAP = 240


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _z(probability: float) -> float:
    p = _clamp(float(probability), 1e-9, 1.0 - 1e-9)
    return statistics.NormalDist().inv_cdf(p)


def _sigmoid(value: float) -> float:
    if value >= 0.0:
        exp_neg = math.exp(-value)
        return 1.0 / (1.0 + exp_neg)
    exp_pos = math.exp(value)
    return exp_pos / (1.0 + exp_pos)


def _round(value: float | None, digits: int = 6) -> float | None:
    if value is None or not math.isfinite(float(value)):
        return None
    return round(float(value), digits)


def dprime_2afc(correct_count: int, n: int) -> float | None:
    """Return d' for a 2-AFC task using a log-linear correction.

    In 2-AFC there is no separate hit/false-alarm pair, so ``d' = sqrt(2) * z(p_correct)`` under the
    equal-variance Gaussian model. The correction keeps the estimate finite with small samples.
    """
    if n <= 0:
        return None
    correct = max(0, min(int(n), int(correct_count)))
    probability = (correct + 0.5) / (n + 1.0)
    return _round(math.sqrt(2.0) * _z(probability))


def side_bias(choices: Iterable[str]) -> float | None:
    """Signed proportion of ``a`` choices minus 0.5.

    This is a response-side bias, not a signal-detection criterion. A value near zero means the two
    sides were used about equally; it does not by itself mean the person was unbiased about content.
    """
    values = [str(choice) for choice in choices if str(choice) in ("a", "b")]
    if not values:
        return None
    return _round(sum(1 for choice in values if choice == "a") / len(values) - 0.5)


def brier_score(pairs: Iterable[tuple[float, bool]]) -> float | None:
    values = [(float(confidence), bool(correct)) for confidence, correct in pairs]
    if not values:
        return None
    return _round(sum((confidence - (1.0 if correct else 0.0)) ** 2 for confidence, correct in values)
                  / len(values))


def overconfidence(pairs: Iterable[tuple[float, bool]]) -> float | None:
    values = [(float(confidence), bool(correct)) for confidence, correct in pairs]
    if not values:
        return None
    mean_confidence = sum(confidence for confidence, _ in values) / len(values)
    accuracy = sum(1.0 for _, correct in values if correct) / len(values)
    return _round(mean_confidence - accuracy)


def type2_auc(confidences: Sequence[float], correct: Sequence[bool]) -> float | None:
    """Non-parametric type-2 AUC for confidence discrimination.

    Returns ``None`` unless there are at least three correct and three incorrect answered trials. The
    measure is descriptive; it is not a meta-d' estimate and it does not identify a metacognitive model.
    """
    if len(confidences) != len(correct):
        return None
    positives = [float(c) for c, ok in zip(confidences, correct) if ok]
    negatives = [float(c) for c, ok in zip(confidences, correct) if not ok]
    if len(positives) < MIN_AUC_CLASS or len(negatives) < MIN_AUC_CLASS:
        return None
    wins = 0.0
    for positive in positives:
        for negative in negatives:
            if positive > negative:
                wins += 1.0
            elif positive == negative:
                wins += 0.5
    return _round(wins / (len(positives) * len(negatives)))


def _log_likelihood(trials: Sequence[Mapping[str, Any]], threshold: float, slope: float,
                    lapse: float) -> float:
    total = 0.0
    for trial in trials:
        delta = float(trial["delta"])
        correct = bool(trial["correct"])
        probability = 0.5 + 0.5 * (1.0 - lapse) * _sigmoid((delta - threshold) / slope)
        probability = _clamp(probability, 1e-9, 1.0 - 1e-9)
        total += math.log(probability) if correct else math.log(1.0 - probability)
    return total


def _fit_grid(trials: Sequence[Mapping[str, Any]], *, lapse: float = DEFAULT_LAPSE,
              threshold_step: float = 0.01, slope_step: float = 0.01) -> dict[str, Any] | None:
    if len(trials) < MIN_THRESHOLD_TRIALS:
        return None
    correct_count = sum(1 for trial in trials if bool(trial["correct"]))
    if correct_count < 2 or len(trials) - correct_count < 2:
        return None
    best: tuple[float, float, float] | None = None
    threshold = 0.02
    while threshold <= 0.9801:
        slope = 0.02
        while slope <= 0.6001:
            score = _log_likelihood(trials, threshold, slope, lapse)
            if best is None or score > best[0] + 1e-12:
                best = (score, threshold, slope)
            slope = round(slope + slope_step, 4)
        threshold = round(threshold + threshold_step, 4)
    if best is None:
        return None
    score, threshold, slope = best
    return {
        "threshold": round(threshold, 4),
        "slope": round(slope, 4),
        "log_likelihood": round(score, 6),
        "n": len(trials),
        "correct": correct_count,
    }


def _percentile(values: Sequence[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * _clamp(fraction, 0.0, 1.0)
    lower = int(math.floor(index))
    upper = int(math.ceil(index))
    if lower == upper:
        return ordered[lower]
    weight = index - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def fit_threshold(trials: Sequence[Mapping[str, Any]], *, lapse: float = DEFAULT_LAPSE,
                  bootstrap: int = DEFAULT_BOOTSTRAP, seed: int = 0) -> dict[str, Any]:
    """Fit the 75%-correct discrimination threshold for one feature.

    Each trial must provide ``delta`` in ``[0, 1]`` and ``correct`` as a bool. Abstentions must be
    removed by the caller. The lower asymptote is fixed at 0.5 because this is a 2-AFC task.
    """
    cleaned = [
        {"delta": float(trial["delta"]), "correct": bool(trial["correct"])}
        for trial in trials
        if trial.get("delta") is not None and trial.get("correct") is not None
    ]
    fit = _fit_grid(cleaned, lapse=lapse)
    if fit is None:
        correct_count = sum(1 for trial in cleaned if bool(trial["correct"]))
        if len(cleaned) >= MIN_THRESHOLD_TRIALS and (
                correct_count >= len(cleaned) - 1 or correct_count <= 1):
            below = correct_count >= len(cleaned) - 1
            return {
                "threshold": 0.02 if below else 0.98,
                "slope": None,
                "ci": None,
                "censored": True,
                "n": len(cleaned),
                "status": "censored",
                "scoring_version": SDT_SCORING_VERSION,
            }
        return {
            "threshold": None,
            "slope": None,
            "ci": None,
            "censored": None,
            "n": len(cleaned),
            "status": "insufficient_evidence",
            "scoring_version": SDT_SCORING_VERSION,
        }
    thresholds: list[float] = []
    if bootstrap > 0:
        rng = random.Random(seed)
        for _ in range(int(bootstrap)):
            sample = [cleaned[rng.randrange(len(cleaned))] for _ in range(len(cleaned))]
            sampled_fit = _fit_grid(sample, lapse=lapse)
            if sampled_fit is not None:
                thresholds.append(sampled_fit["threshold"])
    ci = None
    if len(thresholds) >= max(20, bootstrap // 4):
        low = _percentile(thresholds, 0.025)
        high = _percentile(thresholds, 0.975)
        if low is not None and high is not None:
            ci = [round(low, 4), round(high, 4)]
    threshold = float(fit["threshold"])
    return {
        "threshold": threshold,
        "slope": fit["slope"],
        "ci": ci,
        "censored": bool(threshold <= 0.021 or threshold >= 0.979),
        "n": fit["n"],
        "status": "estimated",
        "scoring_version": SDT_SCORING_VERSION,
    }


def pearson(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 3:
        return None
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_y = sum((y - mean_y) ** 2 for y in ys)
    if var_x <= 1e-12 or var_y <= 1e-12:
        return None
    covariance = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    return _round(covariance / math.sqrt(var_x * var_y))


def fisher_ci(r: float, n: int) -> list[float] | None:
    if n < 4 or abs(r) >= 1.0:
        return None
    z_value = math.atanh(r)
    standard_error = 1.0 / math.sqrt(n - 3)
    low = math.tanh(z_value - 1.96 * standard_error)
    high = math.tanh(z_value + 1.96 * standard_error)
    return [round(low, 6), round(high, 6)]


def test_retest(first: Mapping[str, float], second: Mapping[str, float]) -> dict[str, Any]:
    """Describe test-retest consistency across aligned feature estimates.

    The unit of analysis is the feature, not the person: with one person and two occasions, a
    person-level ICC is not identifiable. The function reports Pearson r across feature estimates,
    the standard error of measurement from difference scores, and the 95% minimal detectable change.
    """
    keys = sorted(set(first) & set(second))
    if len(keys) < 3:
        return {
            "status": "insufficient",
            "reason": "fewer than three aligned features",
            "n_features": len(keys),
            "r": None,
            "r_ci": None,
            "sem": None,
            "mdc95": None,
            "mean_change": None,
        }
    xs = [float(first[key]) for key in keys]
    ys = [float(second[key]) for key in keys]
    correlation = pearson(xs, ys)
    differences = [y - x for x, y in zip(xs, ys)]
    mean_change = sum(differences) / len(differences)
    sd_diff = statistics.pstdev(differences) if len(differences) > 1 else 0.0
    sem = sd_diff / math.sqrt(2.0)
    mdc95 = 1.96 * math.sqrt(2.0) * sem
    return {
        "status": "estimated",
        "reason": None,
        "n_features": len(keys),
        "r": correlation,
        "r_ci": fisher_ci(correlation, len(keys)) if correlation is not None else None,
        "sem": _round(sem),
        "mdc95": _round(mdc95),
        "mean_change": _round(mean_change),
        "features": keys,
    }


def calibration_summary(pairs: Sequence[tuple[float, bool]]) -> dict[str, Any]:
    confidences = [confidence for confidence, _ in pairs]
    correct = [ok for _, ok in pairs]
    return {
        "n": len(pairs),
        "brier": brier_score(pairs),
        "overconfidence": overconfidence(pairs),
        "type2_auc": type2_auc(confidences, correct),
    }


__all__ = [
    "SDT_SCORING_VERSION",
    "DEFAULT_LAPSE",
    "MIN_THRESHOLD_TRIALS",
    "dprime_2afc",
    "side_bias",
    "brier_score",
    "overconfidence",
    "type2_auc",
    "fit_threshold",
    "pearson",
    "fisher_ci",
    "test_retest",
    "calibration_summary",
]
