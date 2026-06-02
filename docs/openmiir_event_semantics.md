# OpenMIIR Event Semantics — V3.9.2

## Discovery Summary (V3.9.1)

In V3.9.1, IMAGINA discovered that all 10 OpenMIIR FIF files contain functioning stim channels
with deterministic event markers — contrary to initial expectations based on missing MNE annotations.

**Key findings:**
- 10/10 subjects have stim channels
- 52 unique event codes discovered via `mne.find_events(raw, stim_channel=..., shortest_event=1)`
- GitHub API tree discovery found 77 candidate metadata files
- MNE `raw.annotations` is empty — stim channel data is the event source, not annotations

## Why Stim Markers Matter

Stim channel event codes are the key to:
1. **Perception vs Imagery analysis** — knowing which EEG windows correspond to which task
2. **Stimulus ID analysis** — identifying which audio/stimulus was presented
3. **Trial onset extraction** — precise event-locked EEG epoching
4. **Behavioral performance** — matching EEG to response times and accuracy

Without semantic labels for these codes, we can only do subject-level sanity checks
(ML classification of which subject produced the EEG), not condition-level analysis.

## Event Codes Discovered

| Family | Codes | Description |
|--------|-------|-------------|
| low_single_digit | 11-14, 21-24, 31-34, 41-44 | Two-digit codes — likely trial-level markers |
| mid_100_range | 111-144 | Three-digit codes — likely stimulus/category identifiers |
| mid_200_range | 211-244 | Three-digit codes — likely imagery/response markers |
| special_markers | 1000, 1111, 2000, 2001 | High-value codes — likely block boundary or session markers |

## Why Semantic Mapping Is Still Unresolved

1. **No trial metadata CSV/TSV files** are directly downloadable from the GitHub repo
   (HTTP 404 at expected paths like `raw.githubusercontent.com/sstober/openmiir/master/meta/trial_info.csv`)
2. **MNE annotations are empty** — no `raw.annotations` data in any FIF file
3. **GitHub metadata candidates** (README.md, paradigm scripts, Jupyter notebooks) contain
   event/stim terms but no explicit `code -> condition_name` lookup tables
4. **Event codes imply structure** but the semantics (which code means "perception",
   which means "imagery", which means "stimulus X") require external documentation

## What Is Needed to Unlock Perception vs Imagery Analysis

1. A documented event code mapping from the OpenMIIR paper or dataset README
2. Contact dataset authors (sstober on GitHub) for the experiment protocol
3. Potentially: inspect OpenMIIR stimulus delivery code to reverse-engineer the marker scheme
4. If available: trial metadata files (`trial_info.csv`, `events_map.csv`, 
   `experiment_meta.json`) with explicit code-to-condition mappings

## How to Manually Provide a condition_manifest.json

If you obtain the correct code mapping, create:

`backend/data/external/openmiir/meta/condition_manifest.json`

```json
{
  "manifest_version": "production",
  "is_production": true,
  "semantic_mapping_confirmed": true,
  "conditions": [
    {
      "condition_id": "perception",
      "event_codes": [11, 12, 13, 14],
      "semantic_label": "Music perception (listening)",
      "confidence": "confirmed"
    },
    {
      "condition_id": "imagery",
      "event_codes": [21, 22, 23, 24],
      "semantic_label": "Music imagery (imagining)",
      "confidence": "confirmed"
    }
  ]
}
```

Then rerun: `python3 -m app.cli.openmiir_condition_eval`

## How to Avoid False Scientific Claims

1. **Do not** claim perception vs imagery EEG differences unless confirmed by semantic mapping
2. **Do not** label event codes based on numerical pattern alone
3. **Always** include the disclaimer: "Experimental proxy features. Not clinical EEG analysis."
4. **Only** use confirmed condition mappings from documentation or dataset authors
5. **Never** present the draft manifest as a production artifact

## Related Artifacts

| Artifact | Path |
|----------|------|
| GitHub tree inventory | `data/external/openmiir/meta/github_tree_inventory.json` |
| Candidate files list | `data/external/openmiir/meta/metadata_candidate_files.json` |
| Candidate content index | `data/external/openmiir/meta/candidate_content_index.json` |
| Stim channel inventory | `data/exports/openmiir_stim_inventory.json` |
| Semantic resolver report | `data/exports/openmiir_semantic_event_resolver.json` |
| Event timing analysis | `data/exports/openmiir_event_timing_analysis.json` |
| Transition matrix | `data/exports/openmiir_event_timing_transition_matrix.csv` |
| Draft condition manifest | `data/exports/openmiir_condition_manifest_draft.json` |
| Condition eval (blocked) | `data/exports/openmiir_condition_eval.json` |
