# Data Dictionary

IMAGINA exports local research data for reproducible analysis. All metrics are experimental proxies and do not represent decoded mental content or clinical evaluation.

| Field | Type | Meaning | Source | Limitation |
|---|---|---|---|---|
| `session_id` | string | Local session identifier | real | Local only |
| `event_type` | string | Event envelope label | real | Depends on runtime flow |
| `timestamp` | ISO datetime | Event timestamp | real | Host clock |
| `iqi` | float 0-1 | Imagery Quality Index proxy | derived | Not validated ground truth |
| `pid` | float 0-1 | Perception-Imagination Distance proxy | derived | Not thought/dream decoding |
| `attention_stability` | float 0-1 | Attention proxy | derived | Simulated/self-report influenced |
| `fatigue` | float 0-1 | Fatigue risk proxy | derived | Not clinical |
| `uncertainty` | float 0-1 | Model uncertainty proxy | derived | Heuristic |
| `signal_quality` | float 0-1 | Signal quality proxy | simulated/derived | Simulated unless real provider added |
| `current_level` | int 1-8 | Curriculum level | derived | Rule-based |
| `self_report.*` | int/text | Subjective user input | user | Subjective |

## V2.1 EEG Metadata Fields (Experimental)

Fields below appear only when a real EEG provider is used in future versions. Default V2.0 simulated/manual/replay sessions do not populate these fields.

| Field | Type | Meaning | Source | Limitation |
|---|---|---|---|---|---|
| `real_signal` | bool | Whether features derive from real EEG (False for simulated/manual) | provider | Requires real LSL provider |
| `provider_id` | string | Signal provider identifier (e.g. `lsl.real`) | provider | Future: LSL stream name |
| `provider_type` | string | `simulated`, `manual`, `replay`, `lsl` | provider | Labels signal source |
| `channel_count` | int >= 0 | Number of EEG channels | LSL stream metadata | Consumer EEG may have 1-4 channels |
| `channel_names` | list[string] | Channel labels (e.g. `AF7`, `TP9`) | LSL stream metadata | Dry EEG label conventions vary |
| `sampling_rate_hz` | float > 0 | EEG sampling rate in Hz | LSL stream metadata | Nominal vs effective may differ |
| `artifact_flags` | list[string] | Detected artifact types (e.g. `blink`, `muscle`) | preprocessing | Heuristic, not clinical |
| `blink_score` | float 0-1 | Estimated blink artifact intensity | derived | Frontal channel heuristic |
| `muscle_score` | float 0-1 | Estimated muscle artifact intensity | derived | High-frequency power ratio |
| `missing_data_ratio` | float 0-1 | Proportion of missing samples in window | derived | Affects signal quality |
| `raw_persisted` | bool | Whether raw EEG samples were persisted | system config | Defaults to False |
| `preprocessing_version` | string | Version tag for preprocessing pipeline | system | Reproducibility metadata |

All real EEG fields are experimental proxy estimates. They do not represent clinical EEG interpretation or decoded mental content.

