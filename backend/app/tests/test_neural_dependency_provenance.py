"""Frozen neural-dependency provenance guard (hermetic; no network, no dataset).

Infrastructure repair only -- this changes NO scientific outcome, threshold, estimator, dataset
contract, ROI, seal, or decision. It exists so that neural-dependency drift fails EARLY and EXPLICITLY
with NEURAL_DEPENDENCY_PROVENANCE_MISMATCH instead of surfacing later as an obscure error inside a
scientific test (as MNE 1.13.1 did in CI run 34617415944: SyntaxError in mne/_fiff/utils.py).

The expected version is read from backend/pyproject.toml (single source of truth) so the pin and this
guard can never disagree. Runs only where the `neural` extra is installed; if MNE is absent the test is
skipped rather than falsely passing.
"""
import re
import sys
from pathlib import Path

import pytest

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - CI runs 3.12
    tomllib = None

_PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"


def _expected_mne_pin() -> str:
    """Return the exact version X from the sole `mne==X` entry in the neural extra."""
    assert _PYPROJECT.exists(), _PYPROJECT
    if tomllib is not None:
        data = tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))
        neural = data["project"]["optional-dependencies"]["neural"]
        pins = [d for d in neural if re.match(r"^\s*mne\s*==", d)]
    else:  # fallback: line scan
        pins = re.findall(r"\"(mne\s*==[^\"]+)\"", _PYPROJECT.read_text(encoding="utf-8"))
    assert len(pins) == 1, f"expected exactly one exact mne== pin in neural extra, found {pins}"
    return pins[0].split("==", 1)[1].strip()


def test_pyproject_pins_mne_exactly():
    # the repair requires an EXACT pin (mne==X), not a range / compatible-release specifier
    expected = _expected_mne_pin()
    assert expected == "1.12.1", (
        f"NEURAL_DEPENDENCY_PROVENANCE_MISMATCH: pyproject mne pin is {expected!r}, "
        "expected exact '1.12.1' for reproducible neural CI"
    )
    raw = _PYPROJECT.read_text(encoding="utf-8")
    assert '"mne==1.12.1"' in raw
    for banned in ('"mne<', '"mne>', '"mne~', '"mne>='):
        assert banned not in raw, f"non-exact mne specifier present: {banned}"


def test_installed_mne_matches_pin():
    mne = pytest.importorskip("mne", reason="neural extra not installed in this job")
    expected = _expected_mne_pin()
    observed = mne.__version__
    assert observed == expected, (
        f"NEURAL_DEPENDENCY_PROVENANCE_MISMATCH: expected MNE {expected}, observed {observed}. "
        "Rebuild the environment against the pinned neural dependencies."
    )


def test_mne_import_and_rawarray_smoke():
    """Direct MNE smoke: the exact operation that raised SyntaxError under 1.13.1 must work."""
    mne = pytest.importorskip("mne", reason="neural extra not installed in this job")
    import numpy as np

    info = mne.create_info(["Cz"], 250.0, ch_types="eeg")
    raw = mne.io.RawArray(np.zeros((1, 250)), info, verbose="ERROR")
    assert raw.n_times == 250
    assert mne.__version__ == _expected_mne_pin()
