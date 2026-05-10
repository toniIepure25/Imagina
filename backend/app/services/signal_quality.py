"""Signal quality evaluation for pre-session / calibration checks."""

from app.schemas.features import FeatureVector


def evaluate_signal_quality(fvs: list[FeatureVector]) -> dict:
    if not fvs:
        return {
            "quality_score": 0.0,
            "warnings": ["insufficient_windows"],
            "summary": {},
        }

    sq = [fv.signal_quality for fv in fvs]
    mdr = [fv.missing_data_ratio or 0 for fv in fvs]
    clip = [fv.clipping_score or 0 for fv in fvs]
    muscle = [fv.muscle_score or 0 for fv in fvs]

    quality_score = sum(sq) / len(sq)
    mean_mdr = sum(mdr) / len(mdr)
    mean_clip = sum(clip) / len(clip)
    mean_muscle = sum(muscle) / len(muscle)

    warnings = []
    if quality_score < 0.4:
        warnings.append("low_signal_quality")
    if mean_mdr > 0.15:
        warnings.append("high_missing_data")
    if mean_clip > 0.10:
        warnings.append("high_clipping")
    if mean_muscle > 0.50:
        warnings.append("high_muscle_noise")
    if len(fvs) < 3:
        warnings.append("insufficient_windows")

    return {
        "quality_score": round(quality_score, 4),
        "warnings": warnings,
        "summary": {
            "signal_quality_mean": round(quality_score, 4),
            "missing_data_ratio_mean": round(mean_mdr, 4),
            "clipping_score_mean": round(mean_clip, 4),
            "muscle_score_mean": round(mean_muscle, 4),
            "windows_evaluated": len(fvs),
        },
    }
