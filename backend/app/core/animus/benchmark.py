"""ANIMUS blind-target benchmark.

Builds hidden target scenes across distinct structural families, wraps the digital twin as a
``RespondentSource``, and runs each controller on each target under fixed seeds. The controller only ever
sees the twin's responses; the evaluator privately compares the final belief to the hidden target. Produces
per-trial metrics used by the acceptance gate. Deterministic under seeds.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.core.animus import metrics, vocab
from app.core.animus.controller import CONTROLLERS
from app.core.animus.loop_runtime import AnimusLoop, LoopConfig
from app.core.animus.models import SOURCE_SIMULATED_NEURAL
from app.core.animus.synthetic_imaginer import ImaginerParams, SyntheticImaginer, TargetScene

SIMILARITY_THRESHOLD = 0.70

TARGET_FAMILIES = [
    "objects", "natural_scene", "room", "synthetic_person", "spatial_layout",
    "colors", "motion", "abstract",
]


def _unit(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-9 else v


def make_target(index: int, seed: int) -> TargetScene:
    """Deterministically construct one hidden target across a rotating family. Non-identifying only."""
    rng = np.random.default_rng(seed * 100003 + index)
    family = TARGET_FAMILIES[index % len(TARGET_FAMILIES)]
    visual = _unit(rng.standard_normal(vocab.VISUAL_EMBED_DIM))
    semantic = _unit(rng.standard_normal(vocab.SEMANTIC_EMBED_DIM))
    attrs = {a: opts[int(rng.integers(len(opts)))] for a, opts in vocab.SCENE_ATTRIBUTES.items()}
    # family-conditioned object subset (kept small; synthetic_person is non-identifying)
    k = int(rng.integers(2, 5))
    objs = set(rng.choice(vocab.OBJECT_VOCAB, size=k, replace=False).tolist())
    label = f"{family}#{index}"
    return TargetScene(visual=visual, semantic=semantic, attributes=attrs, objects=objs, label=label)


class TwinRespondent:
    """Adapts a SyntheticImaginer to the loop's RespondentSource protocol."""

    def __init__(self, imaginer: SyntheticImaginer):
        self.im = imaginer

    def neural_context(self) -> dict:
        return {}

    def comparative(self, cur_emb, prev_emb) -> dict:
        return self.im.compare(np.asarray(cur_emb, float),
                               None if prev_emb is None else np.asarray(prev_emb, float))

    def prefer(self, a_emb, b_emb) -> str:
        return self.im.prefer(np.asarray(a_emb, float), np.asarray(b_emb, float))

    def probe_attribute(self, attr: str) -> dict:
        return self.im.probe_attribute(attr)

    def probe_object(self, obj: str) -> dict:
        return self.im.probe_object(obj)

    def clarity(self, emb) -> float:
        return self.im.clarity(np.asarray(emb, float))

    def fatigue(self) -> float:
        return float(self.im.params.fatigue)


@dataclass
class TrialResult:
    controller: str
    target_label: str
    trial_seed: int
    initial_similarity: float
    final_similarity: float
    loop_gain: float
    attribute_accuracy: float
    object_accuracy: float
    scene_graph_edit_distance: int
    uncertainty_before: float
    uncertainty_after: float
    iterations: int
    iterations_to_threshold: int
    valid: bool
    feedback_count: int
    neural_count: int
    similarity_series: list[float]
    replay_hash: str

    def to_dict(self) -> dict:
        d = self.__dict__.copy()
        for k in ("initial_similarity", "final_similarity", "loop_gain", "attribute_accuracy",
                  "object_accuracy", "uncertainty_before", "uncertainty_after"):
            d[k] = round(float(d[k]), 5)
        d["similarity_series"] = [round(float(x), 5) for x in self.similarity_series]
        return d


def run_trial(controller: str, target: TargetScene, trial_seed: int,
              params: ImaginerParams | None = None, max_iterations: int = 8,
              observation_mode: str | None = SOURCE_SIMULATED_NEURAL) -> TrialResult:
    """Run one blind trial (controller vs hidden target). Evaluator computes similarity privately."""
    params = params or ImaginerParams()
    # fresh, independent twin rng per trial (does not leak into loop determinism)
    twin_rng = np.random.default_rng(trial_seed * 6151 + 17)
    imaginer = SyntheticImaginer(target, ImaginerParams(**params.to_dict()), twin_rng)
    respondent = TwinRespondent(imaginer)
    cfg = LoopConfig(session_id=f"{controller}-{target.label}-{trial_seed}", seed=trial_seed,
                     controller=controller, max_iterations=max_iterations,
                     observation_mode=observation_mode, persist=False)
    loop = AnimusLoop(cfg, respondent, imaginer=imaginer)
    loop.initialize()
    init_sim = metrics.benchmark_similarity(loop.belief, target)
    init_gu = loop.belief.global_uncertainty()
    sim_series = [init_sim]
    it_to_thresh = -1
    while loop.step():
        sim = metrics.benchmark_similarity(loop.belief, target)
        sim_series.append(sim)
        if it_to_thresh < 0 and sim >= SIMILARITY_THRESHOLD:
            it_to_thresh = loop._iter
    final_sim = metrics.benchmark_similarity(loop.belief, target)
    if len(sim_series) == 1 or sim_series[-1] != final_sim:
        sim_series.append(final_sim)
    if it_to_thresh < 0 and final_sim >= SIMILARITY_THRESHOLD:
        it_to_thresh = loop._iter
    fb = sum(1 for e in loop.events if e["event_type"] == "animus.feedback.received")
    nc = sum(1 for e in loop.events if e["event_type"] == "animus.observation.received")
    captured = loop._result(final_state="COMPLETE")
    return TrialResult(
        controller=controller, target_label=target.label, trial_seed=trial_seed,
        initial_similarity=init_sim, final_similarity=final_sim, loop_gain=final_sim - init_sim,
        attribute_accuracy=metrics.attribute_accuracy(loop.belief, target),
        object_accuracy=metrics.object_accuracy(loop.belief, target),
        scene_graph_edit_distance=metrics.scene_graph_edit_distance(loop.belief, target),
        uncertainty_before=init_gu, uncertainty_after=loop.belief.global_uncertainty(),
        iterations=loop._iter,
        iterations_to_threshold=it_to_thresh if it_to_thresh > 0 else max_iterations + 1,
        valid=not captured.aborted, feedback_count=fb, neural_count=nc,
        similarity_series=sim_series, replay_hash=captured.replay_hash())


def run_campaign(n_targets: int = 100, seed_families=(1, 2, 3),
                 controllers: list[str] | None = None, max_iterations: int = 8,
                 params: ImaginerParams | None = None,
                 observation_mode: str | None = SOURCE_SIMULATED_NEURAL) -> dict:
    """Run every controller across n_targets x seed_families. Returns raw per-trial results + config."""
    controllers = controllers or list(CONTROLLERS.keys())
    trials: list[dict] = []
    for fam_seed in seed_families:
        for ti in range(n_targets):
            target = make_target(ti, fam_seed)
            trial_seed = fam_seed * 1_000_000 + ti
            for c in controllers:
                trials.append(run_trial(c, target, trial_seed, params=params,
                                        max_iterations=max_iterations,
                                        observation_mode=observation_mode).to_dict())
    return {"n_targets": n_targets, "seed_families": list(seed_families), "controllers": controllers,
            "max_iterations": max_iterations, "similarity_threshold": SIMILARITY_THRESHOLD,
            "observation_mode": observation_mode,
            "imaginer_params": (params or ImaginerParams()).to_dict(), "trials": trials}
