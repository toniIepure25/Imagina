#!/usr/bin/env python3
"""Generate paper figures from canonical CRT artifacts using only the standard library."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _pairwise(payload: dict) -> dict[str, float]:
    results = payload.get("results") or []
    if not results:
        raise ValueError("artifact has no 'results'")
    pairwise = results[0].get("pairwise_accuracy") or {}
    if not pairwise:
        raise ValueError("artifact has no pairwise_accuracy")
    return {str(key): float(value) for key, value in pairwise.items()}


def _svg(pairs: dict[str, float], source_hash: str) -> str:
    width, height = 980, 460
    left, right, top, bottom = 210, 40, 50, 70
    plot_width = width - left - right
    plot_height = height - top - bottom
    bar_height = min(24, plot_height / max(len(pairs), 1) - 8)
    threshold_x = left + plot_width * 0.85
    rows: list[str] = []
    for index, (label, value) in enumerate(sorted(pairs.items())):
        y = top + index * (plot_height / max(len(pairs), 1))
        bar_width = max(0.0, min(1.0, value)) * plot_width
        color = "#5c7cfa" if value >= 0.85 else "#d78a63"
        rows.append(
            f'<text x="{left - 12}" y="{y + bar_height * 0.75:.1f}" text-anchor="end" '
            f'font-family="monospace" font-size="12" fill="#d8dce8">{html.escape(label)}</text>'
            f'<rect x="{left}" y="{y:.1f}" width="{bar_width:.1f}" height="{bar_height:.1f}" '
            f'fill="{color}" opacity="0.85" />'
            f'<text x="{left + bar_width + 8:.1f}" y="{y + bar_height * 0.75:.1f}" '
            f'font-family="monospace" font-size="12" fill="#d8dce8">{value:.2f}</text>'
        )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<rect width="100%" height="100%" fill="#080a0d"/>
<text x="{left}" y="28" font-family="monospace" font-size="15" fill="#f2ede2">CRT Stage 0I pairwise design accuracy</text>
<line x1="{threshold_x:.1f}" y1="{top - 10}" x2="{threshold_x:.1f}" y2="{height - bottom}" stroke="#e8b45a" stroke-dasharray="5 5" opacity="0.7"/>
<text x="{threshold_x + 6:.1f}" y="{top - 16}" font-family="monospace" font-size="11" fill="#e8b45a">0.85 threshold</text>
{''.join(rows)}
<text x="{left}" y="{height - 24}" font-family="monospace" font-size="10" fill="#8b93a7">simulation-only · source {source_hash[:16]}</text>
</svg>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("results/crt/CRT_STAGE0I_TARGET_DESIGN_READOUT.json"))
    parser.add_argument("--out-dir", type=Path, default=Path("paper/figures"))
    args = parser.parse_args()

    raw = args.input.read_bytes()
    source_hash = hashlib.sha256(raw).hexdigest()
    payload = _load(args.input)
    pairs = _pairwise(payload)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    output = args.out_dir / "fig_stage0i_pairwise.svg"
    output.write_text(_svg(pairs, source_hash), encoding="utf-8")
    print(f"wrote {output} from {args.input} ({source_hash[:16]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
