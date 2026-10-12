"""Phase-2 real-data validation runner.

    python -m app.cli.phase2_validate ecg --root /data/phase2 --out ../results/phase2
    python -m app.cli.phase2_validate eeg --root /data/phase2 --cache /tmp/yoto_epochs.npz --out ../results/phase2
"""
from __future__ import annotations

import argparse
import json
import time
import warnings
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("task", choices=["ecg", "resp", "eda", "eda_bias", "fnirs", "eeg", "meg", "fusion", "latency"])
    ap.add_argument("--root", default="")
    ap.add_argument("--out", default="../results/phase2")
    ap.add_argument("--cache", default="")
    ap.add_argument("--n-perm", type=int, default=100)
    ap.add_argument("--fast", action="store_true")
    args = ap.parse_args()
    warnings.simplefilter("ignore")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    root = Path(args.root)
    t0 = time.time()
    if args.task == "ecg":
        from app.multimodal.validation.ecg_mitdb import run
        print(run(root).write(out / "ecg_mitdb.json"))
    elif args.task == "resp":
        from app.multimodal.validation.resp_bidmc import run
        print(run(root).write(out / "resp_bidmc.json"))
    elif args.task == "eda":
        from app.multimodal.validation.eda_noneeg import run
        print(run(root).write(out / "eda_noneeg.json"))
    elif args.task == "eda_bias":
        from app.multimodal.validation.eda_bias import run
        (out / "eda_synthetic_bias.json").write_text(json.dumps(run(drifts=(0.0, 0.6, 1.2, 2.4)), indent=2))
    elif args.task == "fnirs":
        from app.multimodal.validation.fnirs_motor import run
        print(run(root).write(out / "fnirs_motor.json"))
    elif args.task == "meg":
        from app.multimodal.validation.meg_sample import run
        print(run(root).write(out / "meg_sample.json"))
    elif args.task == "fusion":
        from app.multimodal.validation.fusion_eegmat import run
        print(run(root).write(out / "fusion_eegmat.json"))
    elif args.task == "latency":
        from app.multimodal.validation.latency import run
        (out / "latency_benchmark.json").write_text(json.dumps(run(fast=args.fast), indent=2, default=float))
    elif args.task == "eeg":
        from app.multimodal.validation import eeg_yoto as ey

        es = ey.build_epochs(root / "ds005815", Path(args.cache) if args.cache else None)
        es, exclusions = ey.apply_exclusions(es)
        es.report["exclusions"] = exclusions
        print("epochs", es.x.shape, exclusions, flush=True)
        dataset = {"name": "OpenNeuro ds005815 (YOTO)", "version": "2.0.1",
                   "source": "https://openneuro.org/datasets/ds005815", "license": "CC0",
                   "preprocessing": "1-40 Hz FIR, average reference, 250 Hz, 200 uV ptp rejection",
                   "windows_s": ey.WINDOWS}
        res = ey.run_protocols(es, n_perm=args.n_perm, include_slow=not args.fast)
        print(ey.gate_protocol_a(es, res, dataset).write(out / "eeg_protocol_a.json"))
        print(ey.gate_content(es, res, dataset).write(out / "eeg_imagery_content.json"))
        print(ey.vividness_analysis(es).write(out / "eeg_protocol_b_vividness.json"))
    print(f"done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
