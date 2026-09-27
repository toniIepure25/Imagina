"""ANIMUS-P2-XR dataset I/O adapters (BOLD5000, THINGS-fMRI).

An adapter's ONLY job is to map a dataset's BIDS layout + event table into the frozen P2 measurement
contract: for each valid visual-stimulus presentation, a (onset, duration, stimulus_id) trial, plus the
BOLD/confounds/events run enumeration and a rule to resolve a stimulus_id to its image file (for the frozen
open_clip target embedding).

Adapters MUST NOT change: ROI, HRF, GLM meaning, nuisance logic, target encoder, decoder, metrics, subject
gate or dataset gate. They only translate paths, sessions, runs, event columns and stimulus identifiers.
The normalized (onset, duration, stimulus_id) list is consumed UNCHANGED by
app.research.animus_p2.extract_features_p2r.extract_subject.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass


@dataclass(frozen=True)
class TrialSpec:
    onset: float
    duration: float
    stimulus_id: str
    kind: str  # dataset-specific provenance tag (imagenet/coco/scene | exp/test), never used by the GLM


def _read_tsv(path: str) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def _read_tsv_text(text: str) -> list[dict]:
    return list(csv.DictReader(text.splitlines(), delimiter="\t"))


class DatasetAdapter:
    dataset_id: str = ""
    task: str = ""
    bold_glob: str = ""          # recursive glob for main-task preproc BOLD (MNI space), documented per dataset
    stimulus_id_field: str = ""

    def parse_events(self, events_rows: list[dict]) -> list[TrialSpec]:
        raise NotImplementedError

    def parse_events_file(self, path: str) -> list[TrialSpec]:
        return self.parse_events(_read_tsv(path))

    def parse_events_text(self, text: str) -> list[TrialSpec]:
        return self.parse_events(_read_tsv_text(text))

    def image_relpath(self, stimulus_id: str) -> str:
        """Relative path of the stimulus image within the dataset's staged stimulus store (for CLIP)."""
        raise NotImplementedError


class BOLD5000Adapter(DatasetAdapter):
    """ds001499 v1.3.1. Main task 'task-5000scenes'. Slow event-related (SOA ~10s, dur ~1s).

    events.tsv columns include: onset, duration, ImgName, ImgType (imagenet|coco|scene|...), stim_file.
    Identity = stim_file (the presented image filename). All visual-stimulus rows are valid trials.
    Stimulus images are external (BOLD5000_Stimuli release), staged under a store keyed by ImgType family.
    """
    dataset_id = "ds001499"
    task = "task-5000scenes"
    bold_glob = "**/*task-5000scenes*space-MNI152NLin2009cAsym*preproc_bold.nii.gz"
    stimulus_id_field = "stim_file"

    _IMG_EXT = (".jpg", ".jpeg", ".png")

    def parse_events(self, events_rows: list[dict]) -> list[TrialSpec]:
        trials: list[TrialSpec] = []
        for r in events_rows:
            sid = (r.get("stim_file") or r.get("ImgName") or "").strip()
            if not sid or not sid.lower().endswith(self._IMG_EXT):
                continue
            onset = r.get("onset")
            dur = r.get("duration")
            if onset in (None, "", "n/a") or dur in (None, "", "n/a"):
                continue
            trials.append(TrialSpec(float(onset), float(dur), sid, (r.get("ImgType") or "unknown").strip()))
        return trials

    def image_relpath(self, stimulus_id: str) -> str:
        # BOLD5000_Stimuli organizes images by source family; the id itself encodes the file name.
        s = stimulus_id
        if s.startswith("COCO_"):
            return f"coco/{s}"
        if s.startswith("n") and "_" in s and s.lower().endswith((".jpeg", ".jpg")):
            return f"imagenet/{s}"
        return f"scene/{s}"


class THINGSfMRIAdapter(DatasetAdapter):
    """ds004192 v1.0.7. Main task 'task-things'. Rapid event-related (SOA 4.5s, dur 0.5s).

    events.tsv columns: onset, duration, trial_type (exp|test|catch), category_nr, exemplar_nr,
    test_image_nr, things_category_nr, things_exemplar_nr, response_time, file_path.
    Identity = file_path (e.g. 'dog/dog_12s.jpg'). Keep real object images: trial_type in {exp, test}.
    Exclude 'catch' (attention-check synthetic probes 'catchNNN.jpg' — not real object stimuli).
    THINGS images are external (THINGS object-image database), staged mirroring file_path.
    """
    dataset_id = "ds004192"
    task = "task-things"
    bold_glob = "**/*task-things*space-MNI152NLin2009cAsym*preproc_bold.nii.gz"
    stimulus_id_field = "file_path"

    _KEEP_TRIAL_TYPES = frozenset({"exp", "test"})

    def parse_events(self, events_rows: list[dict]) -> list[TrialSpec]:
        trials: list[TrialSpec] = []
        for r in events_rows:
            ttype = (r.get("trial_type") or "").strip()
            if ttype not in self._KEEP_TRIAL_TYPES:
                continue
            sid = (r.get("file_path") or "").strip()
            if not sid:
                continue
            onset = r.get("onset")
            dur = r.get("duration")
            if onset in (None, "", "n/a") or dur in (None, "", "n/a"):
                continue
            trials.append(TrialSpec(float(onset), float(dur), sid, ttype))
        return trials

    def image_relpath(self, stimulus_id: str) -> str:
        # file_path is already 'concept/concept_NNs.jpg' relative to the THINGS image store.
        return stimulus_id


ADAPTERS = {
    "ds001499": BOLD5000Adapter,
    "ds004192": THINGSfMRIAdapter,
}
