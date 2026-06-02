"""V3.5 representation analysis tests."""

import json
import os
import subprocess
import sys

EXPORTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "exports")
CLI = sys.executable


def test_json_exists():
    assert os.path.exists(os.path.join(EXPORTS, "openmiir_representation_analysis.json"))


def test_md_exists():
    assert os.path.exists(os.path.join(EXPORTS, "openmiir_representation_analysis.md"))


def test_embedding_csv_exists():
    assert os.path.exists(os.path.join(EXPORTS, "openmiir_representation_subject_embeddings.csv"))


def test_similarity_csv_exists():
    assert os.path.exists(os.path.join(EXPORTS, "openmiir_representation_similarity_matrix.csv"))


def test_json_has_range():
    with open(os.path.join(EXPORTS, "openmiir_representation_analysis.json")) as f:
        r = json.load(f)
    lo, hi = r["cosine_similarity_range"]
    assert 0.5 <= hi <= 1.0


def test_no_raw_keys():
    with open(os.path.join(EXPORTS, "openmiir_representation_analysis.json")) as f:
        j = f.read()
    for bad in ("raw_samples", "eeg_samples", "timeseries", "sample_array"):
        assert bad not in j


def test_cli_exits_zero():
    r = subprocess.run(
        [CLI, "-m", "app.cli.eeg_representation_analysis",
         "--dataset", "openmiir", "--max-subjects", "3"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0


def test_figures_exist():
    base = os.path.join(EXPORTS, "figures")
    assert os.path.exists(os.path.join(base, "openmiir_representation_subject_similarity_heatmap.png"))
    assert os.path.exists(os.path.join(base, "openmiir_representation_embedding_pca.png"))
