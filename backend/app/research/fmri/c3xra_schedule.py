"""C3XRA deterministic acquisition-schedule generator (design-only; NO human data).

Generates fully prospective, deterministic per-participant schedules for the sealed C3XRP replication:
imagery units (each identity exactly once per unit; per trial cue -> imagery -> post-video -> evaluation)
and complete-content perception units (fixed consecutive run-pairs; run A and run B disjoint, union = all
identities, one presentation/identity/pair). Everything derives from a frozen master seed + a deterministic
participant-derived seed, so schedules replay bit-identically and no design decision remains after
recruitment. No neural data or outcomes are involved.
"""
from __future__ import annotations

import hashlib

import numpy as np

MASTER_SEED = 20260909
N_IDENTITIES = 72              # VID001..VID072
IMAGERY_TRIALS_PER_RUN = 12   # scanner-feasible run length (~4-5 min); 72/12 = 6 runs/imagery unit
IMAGERY_RUNS_PER_UNIT = N_IDENTITIES // IMAGERY_TRIALS_PER_RUN  # = 6; every identity once per UNIT
PERCEPTION_RUNS_PER_UNIT = 2  # complete-content perception unit = a run-pair (36 + 36 disjoint)


def participant_seed(participant_index: int, master_seed: int = MASTER_SEED) -> int:
    """Deterministic per-participant seed = sha256(master_seed:participant_index) truncated to 63 bits."""
    h = hashlib.sha256(f"{master_seed}:{int(participant_index)}".encode()).hexdigest()
    return int(h[:16], 16) & ((1 << 63) - 1)


def imagery_schedule(participant_index: int, n_units: int, n_id: int = N_IDENTITIES,
                     master_seed: int = MASTER_SEED) -> list[list[int]]:
    """Return n_units imagery-unit orders; each is a permutation of 1..n_id (every identity once/unit)."""
    rng = np.random.default_rng(participant_seed(participant_index, master_seed))
    return [[int(x) for x in rng.permutation(np.arange(1, n_id + 1))] for _ in range(n_units)]


def perception_schedule(participant_index: int, n_units: int, n_id: int = N_IDENTITIES,
                        master_seed: int = MASTER_SEED) -> list[dict]:
    """Return n_units complete-content perception run-pairs. Each pair: run_A (first half of a fresh
    permutation) and run_B (second half) -> disjoint, union = all identities, one presentation/identity."""
    rng = np.random.default_rng(participant_seed(participant_index, master_seed) ^ 0x50455243)
    out = []
    half = n_id // 2
    for u in range(n_units):
        perm = [int(x) for x in rng.permutation(np.arange(1, n_id + 1))]
        out.append({"unit": u + 1, "run_A": perm[:half], "run_B": perm[half:],
                    "runpair_id": (u + 1)})
    return out


def imagery_trials(participant_index: int, n_units: int, n_id: int = N_IDENTITIES,
                   master_seed: int = MASTER_SEED) -> list[dict]:
    """Flatten to per-trial rows: cue/imagery/post-video/evaluation share the trial's identity.

    Each imagery UNIT's fresh 1..n_id permutation is split into IMAGERY_RUNS_PER_UNIT consecutive
    scanner-feasible runs of IMAGERY_TRIALS_PER_RUN trials (every identity once per unit, each in
    exactly one run). run/position balance follows from the uniform random permutation."""
    rows = []
    per_run = IMAGERY_TRIALS_PER_RUN
    for u, order in enumerate(imagery_schedule(participant_index, n_units, n_id, master_seed), start=1):
        for pos, vid in enumerate(order, start=1):
            run = (pos - 1) // per_run + 1
            run_pos = (pos - 1) % per_run + 1
            rows.append({"imagery_unit": u, "run": run, "run_position": run_pos, "position": pos,
                         "video_id": vid, "cue_id": vid, "imagery_id": vid, "postvideo_id": vid,
                         "has_evaluation": True})
    return rows


# ---- contract verification (metadata only) --------------------------------------------------------
def verify_imagery_contract(participant_index: int, n_units: int, n_id: int = N_IDENTITIES) -> dict:
    from collections import Counter
    sched = imagery_schedule(participant_index, n_units, n_id)
    per_unit_ok = all(sorted(u) == list(range(1, n_id + 1)) for u in sched)  # each id exactly once/unit
    total = Counter(v for u in sched for v in u)
    reps_ok = all(total[v] == n_units for v in range(1, n_id + 1))
    return {"n_units": len(sched), "each_unit_has_all_ids_once": per_unit_ok,
            "each_id_reps_equal_units": reps_ok, "n_total_trials": sum(len(u) for u in sched),
            "contract_pass": bool(per_unit_ok and reps_ok and len(sched) == n_units)}


def verify_perception_contract(participant_index: int, n_units: int, n_id: int = N_IDENTITIES) -> dict:
    pairs = perception_schedule(participant_index, n_units, n_id)
    ok = True
    for p in pairs:
        a, b = set(p["run_A"]), set(p["run_B"])
        if not (len(a) == n_id // 2 and len(b) == n_id // 2 and not (a & b)
                and (a | b) == set(range(1, n_id + 1))):
            ok = False
    return {"n_units": len(pairs), "each_pair_72_disjoint_complete": bool(ok),
            "runs_per_unit": PERCEPTION_RUNS_PER_UNIT,
            "contract_pass": bool(ok and len(pairs) == n_units)}


def serial_position_balance(participant_index: int, n_units: int, n_id: int = N_IDENTITIES) -> dict:
    """Each identity should not systematically occupy early/late positions: mean position across units
    per identity should concentrate near the grand mean (n_id+1)/2."""
    sched = imagery_schedule(participant_index, n_units, n_id)
    pos = {v: [] for v in range(1, n_id + 1)}
    for u in sched:
        for p, v in enumerate(u, start=1):
            pos[v].append(p)
    means = np.array([np.mean(pos[v]) for v in range(1, n_id + 1)])
    grand = (n_id + 1) / 2.0
    return {"grand_mean_position": grand, "max_abs_deviation": float(np.max(np.abs(means - grand))),
            "std_of_identity_mean_positions": float(np.std(means))}


def adjacency_confound(participant_index: int, n_units: int, n_id: int = N_IDENTITIES) -> dict:
    """No identity should systematically follow the same predecessor. Max count of any ordered
    (prev,next) identity pair across units should be small (<= n_units)."""
    from collections import Counter
    from itertools import groupby
    rows = imagery_trials(participant_index, n_units, n_id)
    c = Counter()
    def key(r):  # adjacency only within a scanned run
        return (r["imagery_unit"], r["run"])
    for _, grp in groupby(sorted(rows, key=key), key=key):
        seq = [r["video_id"] for r in sorted(grp, key=lambda r: r["run_position"])]
        for i in range(len(seq) - 1):
            c[(seq[i], seq[i + 1])] += 1
    max_pair = max(c.values()) if c else 0
    return {"max_ordered_pair_count": int(max_pair), "n_units": n_units,
            "no_systematic_adjacency": bool(max_pair <= max(2, n_units))}
