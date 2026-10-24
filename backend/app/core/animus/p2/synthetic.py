"""ANIMUS-P2 SYNTHETIC perception dataset (METHOD VALIDATION ONLY — no real images/brains).

Generates a dataset with a KNOWN neural->embedding mapping so the whole sealed pipeline can be proven
correct and leakage-free before touching real data:

* a `signal` subject: neural features are a linear function of the frozen target embedding plus noise, so a
  valid decoder must recover held-out identities (pipeline detects real signal);
* a `null` subject: neural features are independent of the embedding, so the effect must collapse under
  permutation and the subject must FAIL (pipeline does not hallucinate signal).

Everything is deterministic and clearly labelled synthetic.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.core.animus.p2.target_representation import SyntheticStimulusEncoder, unit_l2

N_CATEGORIES = 12


@dataclass
class SyntheticPerceptionSubject:
    subject: str
    X: np.ndarray                # (n_trials, n_vox) neural features
    stimulus_ids: list           # per-trial identity
    Y: np.ndarray                # (n_trials, dim) target embeddings (from frozen encoder)
    categories: list             # per-trial category label
    low_level: np.ndarray        # (n_trials, k) trivial image features


def make_subject(subject: str, n_identities: int = 200, reps: int = 2, n_vox: int = 120,
                 dim: int = 64, signal: float = 1.0, seed: int = 0) -> SyntheticPerceptionSubject:
    enc = SyntheticStimulusEncoder(dim=dim, seed=777)
    rng = np.random.default_rng(seed)
    ids = [f"stim{ i:04d}".replace(" ", "") for i in range(n_identities)]
    emb = enc.embed_many(ids)                                   # (n_id, dim)
    cats = [f"cat{int(i % N_CATEGORIES)}" for i in range(n_identities)]
    # trivial low-level features per identity (independent of embedding)
    low = rng.standard_normal((n_identities, 8))
    # forward operator: embedding -> neural
    A = rng.standard_normal((n_vox, dim)) / np.sqrt(dim)
    X, Y, sid, cat, ll = [], [], [], [], []
    for r in range(reps):
        for k, sid_k in enumerate(ids):
            if signal > 0:
                x = signal * (A @ emb[k]) + 0.9 * rng.standard_normal(n_vox)
            else:
                x = rng.standard_normal(n_vox)                  # null: independent of embedding
            X.append(x)
            Y.append(emb[k])
            sid.append(sid_k)
            cat.append(cats[k])
            ll.append(low[k] + 0.1 * rng.standard_normal(8))
    return SyntheticPerceptionSubject(subject, np.array(X), sid, np.array(Y), cat, np.array(ll))


def unique_gallery(Y: np.ndarray, stimulus_ids: list, keep_ids: list) -> tuple[np.ndarray, list]:
    """One embedding per unique identity in keep_ids (held-out gallery)."""
    keep = set(keep_ids)
    seen = {}
    for y, s in zip(Y, stimulus_ids):
        if s in keep and s not in seen:
            seen[s] = y
    ids = sorted(seen)
    return unit_l2(np.stack([seen[i] for i in ids])), ids
