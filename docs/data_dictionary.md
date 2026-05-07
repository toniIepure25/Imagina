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

