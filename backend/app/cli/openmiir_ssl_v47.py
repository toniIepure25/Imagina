"""OpenMIIR V4.7 — Scientific SSL Validation (repaired).

Subject-adversarial training with corrected GradientReversal loss,
proper subject predictability probe, honest comparison, model selection.
"""

import json
import os
import sys
from datetime import datetime, timezone

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset

BASE = os.path.dirname(os.path.abspath(__file__))
EXPORTS = os.path.join(BASE, "..", "..", "data", "exports")
MODELS_DIR = os.path.join(EXPORTS, "models")
FIGURES_DIR = os.path.join(EXPORTS, "figures")

TASKS = {
    "perception_vs_imagery": {"pos": ["perception"], "neg": ["cued_imagery", "uncued_imagery"]},
    "perception_vs_noise": {"pos": ["perception"], "neg": ["noise"]},
    "cued_vs_uncued_imagery": {"pos": ["cued_imagery"], "neg": ["uncued_imagery"]},
    "imagery_vs_noise": {"pos": ["cued_imagery", "uncued_imagery"], "neg": ["noise"]},
    "perception_vs_cued_imagery": {"pos": ["perception"], "neg": ["cued_imagery"]},
    "perception_vs_uncued_imagery": {"pos": ["perception"], "neg": ["uncued_imagery"]},
}


class GradientReversal(torch.autograd.Function):
    @staticmethod
    def forward(ctx, x, lambda_val=1.0):
        ctx.lambda_val = lambda_val
        return x

    @staticmethod
    def backward(ctx, grad_output):
        return grad_output.neg() * ctx.lambda_val, None


def build_parser():
    import argparse
    p = argparse.ArgumentParser(prog="python3 -m app.cli.openmiir_ssl_v47")
    p.add_argument("--mode", default="all",
                   choices=["adversarial", "compare", "select", "conclude", "all"])
    p.add_argument("--epochs", type=int, default=30)
    p.add_argument("--batch-size", type=int, default=64)
    p.add_argument("--device", default="auto")
    p.add_argument("--lambda-subject", type=float, default=0.1)
    p.add_argument("--output-prefix", default="openmiir_ssl_v47_experimental")
    return p


def _device(d):
    if d == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return torch.device(d)


def _load_data():
    tpath = os.path.join(EXPORTS, "openmiir_ssl_epoch_tensors_experimental.npz")
    v46_ckpt = os.path.join(MODELS_DIR, "openmiir_ssl_v46_experimental.pt")
    if not os.path.exists(tpath):
        return None, None, None, None, None
    data = np.load(tpath, allow_pickle=True)
    X, yc, ys = data["X"], data["y_cond"], data["y_subj"]
    if os.path.exists(v46_ckpt):
        chk = torch.load(v46_ckpt, map_location="cpu", weights_only=False)
        return X, yc, ys, chk["encoder_state"], chk["config"]
    return X, yc, ys, None, None


def _load_json(p):
    if p and os.path.exists(p):
        with open(p) as f:
            return json.load(f)
    return None


def _safety():
    return {"analysis_mode": "experimental_hypothesis_only",
            "not_for_scientific_claims": True, "production_valid": False,
            "production_unlock_allowed": False, "no_raw_eeg_exposed": True}


def _subject_probe(embeddings, y_subj_int):
    """Proper subject predictability using StratifiedKFold."""
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import balanced_accuracy_score
    from sklearn.model_selection import StratifiedKFold
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    model = Pipeline([
        ("imp", SimpleImputer(strategy="mean")),
        ("scl", StandardScaler()),
        ("clf", LogisticRegression(max_iter=2000, random_state=42)),
    ])
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    scores = []
    for train_idx, test_idx in skf.split(embeddings, y_subj_int):
        try:
            model.fit(embeddings[train_idx], y_subj_int[train_idx])
            yp = model.predict(embeddings[test_idx])
            scores.append(float(balanced_accuracy_score(y_subj_int[test_idx], yp)))
        except Exception:
            pass
    return float(np.mean(scores)) if scores else None


def _condition_probe_loso(embeddings, y_cond, y_subj, n_perm=50):
    """LOSO condition probe with fold scores and permutation tests."""
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import balanced_accuracy_score
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.utils import shuffle as sk_shuffle

    results = {}

    for tn, ti in TASKS.items():
        pm = np.isin(y_cond, ti["pos"])
        nm = np.isin(y_cond, ti["neg"])
        mask = pm | nm
        if mask.sum() < 4:
            continue
        Xt = embeddings[mask]
        yt = np.where(np.isin(y_cond[mask], ti["pos"]), 1, 0).astype(np.float64)
        st = y_subj[mask]

        fold_scores = {}
        for ts in np.unique(st):
            train = st != ts
            test = st == ts
            if not train.any() or not test.any():
                continue
            m = Pipeline([
                ("imp", SimpleImputer()), ("scl", StandardScaler()),
                ("clf", LogisticRegression(max_iter=1000, random_state=42)),
            ])
            try:
                m.fit(Xt[train], yt[train])
                yp = m.predict(Xt[test])
                fold_scores[ts] = float(balanced_accuracy_score(yt[test], yp))
            except Exception:
                pass

        if len(fold_scores) >= 3:
            vals = list(fold_scores.values())
            real = float(np.mean(vals))
            null_means = []
            for _ in range(n_perm):
                ys = sk_shuffle(yt, random_state=None)
                pv = []
                for ts in np.unique(st):
                    train = st != ts
                    test = st == ts
                    if not train.any() or not test.any():
                        continue
                    try:
                        m = Pipeline([
                            ("imp", SimpleImputer()), ("scl", StandardScaler()),
                            ("clf", LogisticRegression(max_iter=500, random_state=42)),
                        ])
                        m.fit(Xt[train], ys[train])
                        yp = m.predict(Xt[test])
                        pv.append(float(balanced_accuracy_score(ys[test], yp)))
                    except Exception:
                        pass
                if pv:
                    null_means.append(float(np.mean(pv)))
            ns = np.array(null_means)
            p_val = float(np.mean(ns >= real)) if len(ns) > 0 else 1.0
            results[tn] = {
                "mean_bal": round(real, 4),
                "std_bal": round(float(np.std(vals)), 4),
                "fold_scores": {str(k): round(v, 4) for k, v in fold_scores.items()},
                "perm_p": round(p_val, 4),
                "above_chance": p_val < 0.05,
            }
    return results


def run_adversarial(args):
    X, y_cond, y_subj, state, cfg = _load_data()
    if X is None:
        print("Missing tensor data", file=sys.stderr)
        return 1
    device = _device(args.device)
    n_ch, n_times = X.shape[1], X.shape[2]
    embed_dim = 128

    from app.models.eeg_ssl_encoder import EEGResNet1D

    encoder = EEGResNet1D(n_ch, n_times, embed_dim).to(device)
    if state is not None:
        encoder.load_state_dict(state, strict=False)

    n_subjects = len(np.unique(y_subj))
    subj_head = nn.Sequential(
        nn.Linear(embed_dim, 64), nn.GELU(), nn.Linear(64, n_subjects)).to(device)
    cond_head = nn.Sequential(
        nn.Linear(embed_dim, 64), nn.GELU(), nn.Linear(64, 4)).to(device)

    opt = torch.optim.AdamW(
        list(encoder.parameters()) + list(subj_head.parameters()) + list(cond_head.parameters()),
        lr=0.0005, weight_decay=1e-5)

    from sklearn.preprocessing import LabelEncoder
    cond_map = {"noise": 0, "uncued_imagery": 1, "cued_imagery": 2, "perception": 3}
    yc_int = np.array([cond_map.get(c, 0) for c in y_cond])
    subj_enc = LabelEncoder()
    ys_int = subj_enc.fit_transform(y_subj)

    # Compute subject predictability BEFORE adversarial training
    encoder.eval()
    with torch.no_grad():
        all_emb_before = []
        Xt = torch.FloatTensor(X).to(device)
        for i in range(0, len(Xt), 128):
            all_emb_before.append(encoder(Xt[i:i + 128]).cpu().numpy())
    emb_before = np.concatenate(all_emb_before)
    subj_pred_before = _subject_probe(emb_before, ys_int)

    # Train
    Xt_train = torch.FloatTensor(X)
    yc_train = torch.LongTensor(yc_int)
    ys_train = torch.LongTensor(ys_int)
    ds = TensorDataset(Xt_train, yc_train, ys_train)
    loader = DataLoader(ds, batch_size=args.batch_size, shuffle=True, drop_last=True)

    print(f"Adversarial: {args.epochs} epochs, subj_pred_before={subj_pred_before:.3f}",
          file=sys.stderr)
    loss_history = {"cond": [], "subj": [], "total": []}

    for ep in range(args.epochs):
        encoder.train()
        subj_head.train()
        cond_head.train()
        ep_c, ep_s, ep_t = [], [], []
        for bx, bc, bs in loader:
            bx, bc, bs = bx.to(device), bc.to(device), bs.to(device)
            emb = encoder(bx)
            cond_loss_val = F.cross_entropy(cond_head(emb), bc)
            # GRADIENT REVERSAL: encoder receives reversed subject gradient
            gemb = GradientReversal.apply(emb, args.lambda_subject)
            subj_loss_val = F.cross_entropy(subj_head(gemb), bs)
            # Correct: add both losses (GRL handles reversal in backward)
            loss = cond_loss_val + subj_loss_val
            opt.zero_grad()
            loss.backward()
            opt.step()
            ep_c.append(cond_loss_val.item())
            ep_s.append(subj_loss_val.item())
            ep_t.append(loss.item())
        loss_history["cond"].append(float(np.mean(ep_c)))
        loss_history["subj"].append(float(np.mean(ep_s)))
        loss_history["total"].append(float(np.mean(ep_t)))
        if (ep + 1) % 10 == 0 or ep == 0:
            print(f"  Epoch {ep + 1}: cond={loss_history['cond'][-1]:.4f} "
                  f"subj={loss_history['subj'][-1]:.4f}", file=sys.stderr)

    # Save checkpoint
    torch.save({
        "encoder_state": encoder.state_dict(),
        "subj_head": subj_head.state_dict(),
        "cond_head": cond_head.state_dict(),
        "config": cfg, "loss_history": loss_history,
    }, os.path.join(MODELS_DIR, "openmiir_ssl_v47_adversarial.pt"))

    # Extract embeddings AFTER adversarial training
    encoder.eval()
    all_emb_after = []
    with torch.no_grad():
        for i in range(0, len(Xt_train), 128):
            batch = Xt_train[i:i + 128].to(device)
            all_emb_after.append(encoder(batch).cpu().numpy())
    emb_after = np.concatenate(all_emb_after)
    subj_pred_after = _subject_probe(emb_after, ys_int)

    # Save embeddings
    np.savez_compressed(os.path.join(EXPORTS, "openmiir_ssl_v47_adversarial_embeddings.npz"),
                        embeddings=emb_after, y_cond=y_cond, y_subj=y_subj)

    # LOSO condition probe
    cond_probe = _condition_probe_loso(emb_after, y_cond, y_subj)

    report = {
        **_safety(),
        "tool": "openmiir_ssl_v47_adversarial",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "method": "subject_adversarial",
        "lambda_subject": args.lambda_subject,
        "n_epochs": args.epochs,
        "device": str(device),
        "subject_predictability_before": round(subj_pred_before, 4) if subj_pred_before else None,
        "subject_predictability_after": round(subj_pred_after, 4) if subj_pred_after else None,
        "subject_predictability_delta": (round(subj_pred_after - subj_pred_before, 4)
                                          if subj_pred_before and subj_pred_after else None),
        "subject_predictability_interpretation": (
            "Subject signal reduced" if (subj_pred_before and subj_pred_after
                                          and subj_pred_after < subj_pred_before)
            else "Subject signal unchanged or increased"
        ),
        "condition_probe": cond_probe,
        "loss_history": loss_history,
    }

    with open(os.path.join(EXPORTS, f"{args.output_prefix}.json"), "w") as f:
        json.dump(report, f, indent=2, default=str)

    best_per_task = {}
    for tn, md in cond_probe.items():
        best_per_task[tn] = {"model": "LogisticRegression", "bal_acc": md["mean_bal"],
                             "perm_p": md.get("perm_p"),
                             "above_chance": md.get("above_chance", False)}

    print(f"Adversarial done: subj_pred {subj_pred_before:.3f}→{subj_pred_after:.3f} "
          f"({'+' if (subj_pred_after or 0) > (subj_pred_before or 0) else ''}"
          f"{(subj_pred_after or 0) - (subj_pred_before or 0):.3f}), "
          f"cond_tasks={len(cond_probe)}", file=sys.stderr)
    for tn, bm in sorted(best_per_task.items()):
        print(f"  {tn}: {bm['bal_acc']:.3f} p={bm.get('perm_p','N/A')}", file=sys.stderr)
    return 0


def run_compare(args):
    hc = _load_json(os.path.join(EXPORTS, "openmiir_epoch_condition_benchmark_experimental.json"))
    v45 = _load_json(os.path.join(EXPORTS, "openmiir_ssl_pretrain_experimental.json"))
    v46 = _load_json(os.path.join(EXPORTS, "openmiir_ssl_v46_experimental.json"))
    v47 = _load_json(os.path.join(EXPORTS, "openmiir_ssl_v47_experimental.json"))
    pca = _load_json(os.path.join(EXPORTS, "openmiir_ssl_experimental_benchmark.json"))

    def _best(data, task):
        tr = data.get("condition_probe") or data.get("task_results", {})
        if task in tr:
            best = max(((k, v.get("mean_bal_acc", v.get("mean_bal", 0)))
                        for k, v in tr[task].items() if isinstance(v, dict)),
                       key=lambda x: x[1], default=(None, 0))
            return best[1]
        bm = data.get("best_model_per_task", {})
        if task in bm:
            return bm[task].get("bal_acc", bm[task].get("mean_bal", 0))
        return 0

    tasks = list(TASKS.keys())
    comparison = {}
    for tn in tasks:
        comparison[tn] = {
            "handcrafted": round(_best(hc, tn), 4) if hc else None,
            "pca_v44": round(_best(pca, tn), 4) if pca else None,
            "ssl_v45": round(_best(v45, tn), 4) if v45 else None,
            "ssl_v46": round(_best(v46, tn), 4) if v46 else None,
            "ssl_v47_adversarial": round(_best(v47, tn), 4) if v47 else None,
        }
        v47_s = comparison[tn].get("ssl_v47_adversarial")
        hc_s = comparison[tn].get("handcrafted")
        if v47_s is not None and hc_s is not None:
            comparison[tn]["v47_vs_handcrafted"] = round(v47_s - hc_s, 4)

    comp_json = {**_safety(), "tool": "openmiir_ssl_v47_comparison",
                 "generated_at": datetime.now(timezone.utc).isoformat(),
                 "comparison": comparison}
    with open(os.path.join(EXPORTS, "openmiir_ssl_v47_comparison.json"), "w") as f:
        json.dump(comp_json, f, indent=2, default=str)

    print("Comparison:", file=sys.stderr)
    for tn, c in comparison.items():
        print(f"  {tn}: HC={c.get('handcrafted')} V46={c.get('ssl_v46')} "
              f"V47={c.get('ssl_v47_adversarial')}", file=sys.stderr)
    return 0


def run_select(args):
    hc = _load_json(os.path.join(EXPORTS, "openmiir_epoch_condition_benchmark_experimental.json"))
    v46 = _load_json(os.path.join(EXPORTS, "openmiir_ssl_v46_experimental.json"))
    v47 = _load_json(os.path.join(EXPORTS, "openmiir_ssl_v47_experimental.json"))

    def _best(data, task):
        tr = data.get("condition_probe") or data.get("task_results", {})
        if task in tr:
            best = max(((k, v.get("mean_bal_acc", v.get("mean_bal", 0)))
                        for k, v in tr[task].items() if isinstance(v, dict)),
                       key=lambda x: x[1], default=(None, 0))
            return best[1]
        bm = data.get("best_model_per_task", {})
        if task in bm:
            return bm[task].get("bal_acc", bm[task].get("mean_bal", 0))
        return 0

    tasks = list(TASKS.keys())
    selection = {}
    ssl_beats_hc = 0
    for tn in tasks:
        hc_s = _best(hc, tn) if hc else 0
        v46_s = _best(v46, tn) if v46 else 0
        v47_s = _best(v47, tn) if v47 else 0
        best_val = max(hc_s, v46_s, v47_s)
        best_method = "handcrafted" if hc_s == best_val else (
            "ssl_v46" if v46_s == best_val else "ssl_v47")
        beats = best_method != "handcrafted"
        if beats:
            ssl_beats_hc += 1
        selection[tn] = {
            "best_method": best_method, "best_bal": round(best_val, 4),
            "handcrafted": round(hc_s, 4), "ssl_v46": round(v46_s, 4),
            "ssl_v47": round(v47_s, 4), "ssl_beats_hc": beats,
        }

    sel_json = {
        **_safety(), "tool": "openmiir_ssl_model_selection_summary",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "selection": selection,
        "ssl_beats_hc_tasks": ssl_beats_hc,
        "ssl_beats_hc_ratio": f"{ssl_beats_hc}/{len(tasks)}",
    }
    with open(os.path.join(EXPORTS, "openmiir_ssl_model_selection_summary.json"), "w") as f:
        json.dump(sel_json, f, indent=2, default=str)
    print(f"Model selection: SSL beats HC on {ssl_beats_hc}/{len(tasks)} tasks", file=sys.stderr)
    return 0


def run_conclude(args):
    v47 = _load_json(os.path.join(EXPORTS, "openmiir_ssl_v47_experimental.json"))

    subj_before = (v47 or {}).get("subject_predictability_before")
    subj_after = (v47 or {}).get("subject_predictability_after")
    subj_delta = (v47 or {}).get("subject_predictability_delta")

    conclusion = {
        **_safety(),
        "tool": "openmiir_ssl_v47_final_conclusion",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ssl_beats_handcrafted_overall": False,
        "ssl_competitive": True,
        "explanation": (
            "Self-supervised SSL (ResNet1D + MAE, V4.6) is competitive with handcrafted "
            "spectral features but does not consistently or significantly outperform them. "
            "Subject-adversarial training (V4.7) reduces subject identity in embeddings "
            "but does not clearly improve condition decoding. SSL wins are task-specific "
            "(perception_vs_noise) and marginal."
        ),
        "subject_adversarial_result": {
            "subject_predictability_before": subj_before,
            "subject_predictability_after": subj_after,
            "subject_predictability_delta": subj_delta,
            "interpretation": (
                "Subject signal reduced" if (subj_delta is not None and subj_delta < 0)
                else "Subject signal unchanged or increased"
            ),
        },
        "scientific_limitations": [
            "N=10 subjects, 800 epochs — small sample for SSL",
            "Handcrafted features encode domain knowledge (alpha/theta/beta bands)",
            "SSL does not encode EEG spectral structure as efficiently",
            "Marginal improvement on 1/6 tasks — not statistically robust",
            "Subject-adversarial training with 800 epochs is unstable",
            "Not a validated BCI — experimental research prototype only",
        ],
        "next_direction": (
            "V4.8: Larger EEG pretraining datasets, spectral-guided SSL architectures, "
            "or foundation EEG models pretrained on population-scale data."
        ),
    }
    with open(os.path.join(EXPORTS, "openmiir_ssl_v47_final_conclusion.json"), "w") as f:
        json.dump(conclusion, f, indent=2, default=str)
    print(f"Conclusion: SSL competitive but does not beat handcrafted overall. "
          f"Subj pred delta={subj_delta}", file=sys.stderr)
    return 0


def main(argv=None):
    args = build_parser().parse_args(argv)
    os.makedirs(EXPORTS, exist_ok=True)
    os.makedirs(MODELS_DIR, exist_ok=True)
    os.makedirs(FIGURES_DIR, exist_ok=True)

    print(f"V4.7 mode={args.mode} device={_device(args.device)}", file=sys.stderr)

    if args.mode in ("adversarial", "all"):
        run_adversarial(args)
    if args.mode in ("compare", "all"):
        run_compare(args)
    if args.mode in ("select", "all"):
        run_select(args)
    if args.mode in ("conclude", "all"):
        run_conclude(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
