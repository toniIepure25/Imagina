"""Perception-imagery representation transfer for Scientific Gate C1 (H3/H4).

Implements RSA, CKA, cross-state retrieval, a simplified temporal
generalization check, and subject-level alignment summaries. A perception
encoder is trained (or reused from Commit 5) using ONLY perception-condition
trials; its frozen representation is then evaluated on imagery-condition
trials — imagery labels never enter perception pretraining, per
`C1_PROTOCOL.md` H3.

Not implemented: the "optional" frozen visual-semantic image encoder target.
ds005815 does not distribute the actual stimulus images (only descriptive
categories decoded in `trigger_codebook.py`), and adding a large pretrained
image encoder dependency (e.g. CLIP) for a handful of geometric/face stimuli
with no source images available was judged not worth the dependency weight
for an explicitly optional component — recorded here, not silently dropped.

Representational similarity is descriptive, not causal evidence, per
`C1_PROTOCOL.md` H4 — nothing in this module supports a causal claim.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.stats import spearmanr


def embed_with_eegnet(model, x: np.ndarray) -> np.ndarray:
    """Extract the penultimate-layer representation (post-pool, pre-head)
    from a fitted `EEGNetBaseline` — the natural embedding for RSA/CKA."""
    torch = __import__("torch")
    model.net.eval()
    with torch.no_grad():
        x_t = torch.tensor(x, dtype=torch.float32).unsqueeze(1)
        return model.net._forward_features(x_t).numpy()


def representational_dissimilarity_matrix(embeddings: np.ndarray) -> np.ndarray:
    """Pairwise 1 - cosine-similarity matrix, the standard RSA input."""
    norm = embeddings / (np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-12)
    sim = norm @ norm.T
    return 1.0 - sim


def rsa(embeddings_a: np.ndarray, embeddings_b: np.ndarray) -> float:
    """Representational similarity analysis: Spearman correlation between
    the upper triangles of two conditions' representational dissimilarity
    matrices, computed over the SAME set of stimulus identities in the SAME
    order. Returns NaN if fewer than 3 items (no meaningful RDM)."""
    if embeddings_a.shape[0] != embeddings_b.shape[0] or embeddings_a.shape[0] < 3:
        return float("nan")
    rdm_a = representational_dissimilarity_matrix(embeddings_a)
    rdm_b = representational_dissimilarity_matrix(embeddings_b)
    n = rdm_a.shape[0]
    iu = np.triu_indices(n, k=1)
    rho, _p = spearmanr(rdm_a[iu], rdm_b[iu])
    return float(rho)


def linear_cka(x: np.ndarray, y: np.ndarray) -> float:
    """Centered kernel alignment (linear kernel), Kornblith et al. 2019.
    x: (n_samples, d1), y: (n_samples, d2), same n_samples (paired samples,
    not necessarily the same stimuli count as RSA's per-condition means)."""
    def _centered_gram(a):
        k = a @ a.T
        n = k.shape[0]
        unit = np.ones((n, n)) / n
        return k - unit @ k - k @ unit + unit @ k @ unit

    kx = _centered_gram(x)
    ky = _centered_gram(y)
    hsic_xy = np.sum(kx * ky)
    hsic_xx = np.sum(kx * kx)
    hsic_yy = np.sum(ky * ky)
    denom = np.sqrt(hsic_xx * hsic_yy)
    if denom == 0:
        return 0.0
    return float(hsic_xy / denom)


def cross_state_retrieval_accuracy(
    perception_embeddings: np.ndarray, perception_stimulus_ids: list[str],
    imagery_embeddings: np.ndarray, imagery_stimulus_ids: list[str],
) -> float:
    """For each imagery embedding, retrieve the nearest-neighbor perception
    embedding (cosine distance) and check whether its stimulus_id matches.
    Chance level is 1/n_unique_stimuli, not 0.5 — callers should compare
    against that, not an arbitrary threshold."""
    if len(imagery_embeddings) == 0 or len(perception_embeddings) == 0:
        return float("nan")
    p_norm = perception_embeddings / (np.linalg.norm(perception_embeddings, axis=1, keepdims=True) + 1e-12)
    i_norm = imagery_embeddings / (np.linalg.norm(imagery_embeddings, axis=1, keepdims=True) + 1e-12)
    sims = i_norm @ p_norm.T  # (n_imagery, n_perception)
    nearest = np.argmax(sims, axis=1)
    correct = sum(
        1 for i, j in enumerate(nearest) if imagery_stimulus_ids[i] == perception_stimulus_ids[j]
    )
    return correct / len(imagery_stimulus_ids)


def chance_retrieval_accuracy(stimulus_ids: list[str]) -> float:
    return 1.0 / max(len(set(stimulus_ids)), 1)


@dataclass
class TemporalGeneralizationResult:
    train_window_centers_s: np.ndarray
    test_window_centers_s: np.ndarray
    accuracy_matrix: np.ndarray  # (n_train_windows, n_test_windows)

    def to_dict(self) -> dict[str, Any]:
        return {
            "train_window_centers_s": self.train_window_centers_s.tolist(),
            "test_window_centers_s": self.test_window_centers_s.tolist(),
            "accuracy_matrix": self.accuracy_matrix.tolist(),
        }


def temporal_generalization_matrix(
    epochs: np.ndarray, labels: np.ndarray, sfreq: float, window_s: float = 0.2, step_s: float = 0.2,
) -> TemporalGeneralizationResult:
    """A simplified temporal generalization matrix (King & Dehaene 2014
    style): a linear classifier is fit per time window on mean band-agnostic
    per-channel amplitude, then evaluated (in-sample here — this is a
    descriptive diagnostic, not the confirmatory Commit 7 estimate, which
    uses proper nested CV) at every other time window. `epochs`:
    (n_trials, n_channels, n_samples), `labels`: binary array (n_trials,).
    """
    from sklearn.linear_model import LogisticRegression

    n_samples = epochs.shape[-1]
    window_samples = max(1, int(window_s * sfreq))
    step_samples = max(1, int(step_s * sfreq))
    starts = list(range(0, max(n_samples - window_samples, 1), step_samples)) or [0]
    centers_s = np.array([(s + window_samples / 2) / sfreq for s in starts])

    window_features = []
    for s in starts:
        seg = epochs[:, :, s:s + window_samples]
        window_features.append(seg.mean(axis=2))  # (n_trials, n_channels)

    n_windows = len(starts)
    acc = np.zeros((n_windows, n_windows))
    if len(set(labels.tolist())) < 2:
        return TemporalGeneralizationResult(centers_s, centers_s, acc)

    models = []
    for train_feat in window_features:
        clf = LogisticRegression(max_iter=200)
        clf.fit(train_feat, labels)
        models.append(clf)

    for i, clf in enumerate(models):
        for j, test_feat in enumerate(window_features):
            acc[i, j] = clf.score(test_feat, labels)

    return TemporalGeneralizationResult(centers_s, centers_s, acc)


@dataclass
class SubjectAlignmentSummary:
    participant_id: str
    rsa_perception_imagery: float
    cka_perception_imagery: float
    cross_state_retrieval_accuracy: float
    chance_retrieval_accuracy: float

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


def summarize_alignment_across_subjects(
    summaries: list[SubjectAlignmentSummary],
) -> dict[str, Any]:
    """Aggregate subject-level alignment summaries — the participant is the
    inferential unit here too, per C1_PROTOCOL.md Section 6: this reports
    a distribution across participants, not a trial-pooled number."""
    if not summaries:
        return {"n_participants": 0}
    retrieval = np.array([s.cross_state_retrieval_accuracy for s in summaries])
    rsa_vals = np.array([s.rsa_perception_imagery for s in summaries if not np.isnan(s.rsa_perception_imagery)])
    cka_vals = np.array([s.cka_perception_imagery for s in summaries])
    return {
        "n_participants": len(summaries),
        "retrieval_accuracy_mean": float(retrieval.mean()),
        "retrieval_accuracy_std": float(retrieval.std()),
        "rsa_mean": float(rsa_vals.mean()) if len(rsa_vals) else None,
        "cka_mean": float(cka_vals.mean()),
        "cka_std": float(cka_vals.std()),
        "per_participant": [s.to_dict() for s in summaries],
    }
