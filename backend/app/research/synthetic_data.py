from __future__ import annotations

import random
import uuid
from datetime import datetime, timezone


def generate_synthetic_dataset(
    n_participants: int = 24,
    n_sessions_per_condition: int = 3,
    trials_per_session: int = 5,
    conditions: list[str] | None = None,
    seed: int = 42,
) -> dict:
    """Generate synthetic research data mirroring the expected schema.

    Produces plausible-but-fake data for:
    - Self-report vividness (1-7 Likert)
    - Confidence ratings (1-7 Likert)
    - Effort ratings (1-7 Likert)
    - IQI proxy (0-1)
    - PID proxy (0-1)
    - Behavioral consistency (0-1)
    - Pre/post VVIQ-2 scores (16-80)

    Adaptive condition shows a small improvement effect (Cohen's d ~ 0.4),
    fixed condition shows a smaller improvement (practice effect, d ~ 0.15),
    yoked condition is flat.
    """
    if conditions is None:
        conditions = ["adaptive", "fixed", "yoked"]

    rng = random.Random(seed)
    participants = []
    trial_data = []

    for p_idx in range(n_participants):
        p_id = f"P{p_idx + 1:03d}"
        p_seed = rng.randint(0, 2**31)
        p_rng = random.Random(p_seed)

        baseline_vividness = p_rng.gauss(4.0, 0.8)
        baseline_vviq = max(16, min(80, int(p_rng.gauss(48, 12))))

        for c_idx, condition in enumerate(conditions):
            for s_idx in range(n_sessions_per_condition):
                session_id = str(uuid.UUID(int=p_rng.getrandbits(128)))

                improvement = _condition_effect(condition, s_idx, n_sessions_per_condition)

                for t_idx in range(trials_per_session):
                    trial_noise = p_rng.gauss(0, 0.3)

                    vividness = max(1, min(7, round(baseline_vividness + improvement + trial_noise)))
                    conf_raw = baseline_vividness * 0.8 + improvement * 0.5 + p_rng.gauss(0, 0.4)
                    confidence = max(1, min(7, round(conf_raw)))
                    effort = max(1, min(7, round(4.0 + p_rng.gauss(0, 0.8))))

                    iqi = max(0.0, min(1.0, 0.45 + improvement * 0.1 + p_rng.gauss(0, 0.08)))
                    pid = max(0.0, min(1.0, 0.40 - improvement * 0.08 + p_rng.gauss(0, 0.07)))
                    behavioral = max(0.0, min(1.0, 0.55 + improvement * 0.06 + p_rng.gauss(0, 0.06)))

                    trial_data.append({
                        "participant_id": p_id,
                        "condition": condition,
                        "session_index": s_idx,
                        "session_id": session_id,
                        "trial_index": t_idx,
                        "vividness": vividness,
                        "confidence": confidence,
                        "effort": effort,
                        "iqi": round(iqi, 4),
                        "pid": round(pid, 4),
                        "behavioral_consistency": round(behavioral, 4),
                    })

        post_vviq_change = _vviq_change(conditions, p_rng)
        post_vviq = max(16, min(80, baseline_vviq + post_vviq_change))

        participants.append({
            "participant_id": p_id,
            "seed": p_seed,
            "baseline_vividness": round(baseline_vividness, 2),
            "pre_vviq2": baseline_vviq,
            "post_vviq2": post_vviq,
            "vviq2_change": post_vviq - baseline_vviq,
        })

    return {
        "metadata": {
            "generator": "imagina_synthetic_data",
            "version": "1.0",
            "seed": seed,
            "n_participants": n_participants,
            "n_sessions_per_condition": n_sessions_per_condition,
            "trials_per_session": trials_per_session,
            "conditions": conditions,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "participants": participants,
        "trials": trial_data,
    }


def _condition_effect(condition: str, session_idx: int, total_sessions: int) -> float:
    progress = session_idx / max(1, total_sessions - 1)
    if condition == "adaptive":
        return 0.8 * progress
    elif condition == "fixed":
        return 0.3 * progress
    else:
        return 0.05 * progress


def _vviq_change(conditions: list[str], rng: random.Random) -> int:
    if "adaptive" in conditions:
        return int(rng.gauss(3.0, 2.5))
    elif "fixed" in conditions:
        return int(rng.gauss(1.0, 2.0))
    return int(rng.gauss(0.0, 1.5))


def export_to_csv_rows(dataset: dict) -> tuple[list[dict], list[dict]]:
    return dataset["participants"], dataset["trials"]
