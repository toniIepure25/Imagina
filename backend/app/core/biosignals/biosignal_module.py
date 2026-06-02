"""IMAGINA V28 — Biosignal Adapter + Simulated Source + LSL/BrainFlow + Signal Quality + Marker Sync + Monitor + Report."""

import json
import math
import os
import random
from datetime import datetime, timezone
from uuid import uuid4

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..",
                    "data", "imagina", "biosignals")

SAFETY = {
    "analysis_mode": "personal_exploratory_training",
    "not_clinical": True, "not_diagnostic": True,
    "not_mind_reading": True, "not_bci_claim": True,
    "not_neurofeedback_claim": True,
    "production_valid": False,
    "scientific_boundary": ("Personal exploratory adaptive mental imagery training only. "
                             "Not diagnosis, therapy, clinical treatment, "
                             "mind-reading, dream decoding, validated BCI, or validated neurofeedback."),
    "biosignal_boundary": ("Biosignal streaming is optional and exploratory. Signal quality summaries "
                            "are engineering diagnostics, not neural decoding, diagnosis, treatment, "
                            "or validated neurofeedback."),
    "raw_eeg_export_default": False,
}


def _load_json(p):
    return json.load(open(p)) if os.path.exists(p) else None


def _save_json(p, data):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        json.dump(data, f, indent=2, default=str)


def _append_jsonl(p, entry):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "a") as f:
        f.write(json.dumps(entry, default=str) + "\n")


# ─── SOURCE REGISTRY ────────────────────────────────────────────

def _registry_path():
    return os.path.join(BASE, "source_registry.json")


def register_biosignal_source(source_config):
    sid = source_config.get("source_id", str(uuid4()))
    default = {"source_id": sid, "source_type": "simulated", "sampling_rate_hz": 250,
               "n_channels": 8, "channel_names": [f"ch{i+1}" for i in range(8)],
               "enabled": True, "raw_recording_enabled": False, "safe_public_export": False,
               "status": "created", "created_at": datetime.now(timezone.utc).isoformat()}
    config = {**default, **source_config}
    d = os.path.join(BASE, "sources", sid)
    _save_json(os.path.join(d, "source_config.json"), config)
    reg = _load_json(_registry_path()) or {"sources": {}}
    reg["sources"][sid] = config
    _save_json(_registry_path(), reg)
    return {**config, **SAFETY}


def get_biosignal_source(source_id):
    p = os.path.join(BASE, "sources", source_id, "source_config.json")
    return _load_json(p)


def list_biosignal_sources():
    reg = _load_json(_registry_path())
    return (reg or {}).get("sources", {})


def remove_biosignal_source(source_id):
    p = os.path.join(BASE, "sources", source_id)
    if os.path.exists(p):
        import shutil
        shutil.rmtree(p, ignore_errors=True)
        reg = _load_json(_registry_path()) or {}
        reg["sources"].pop(source_id, None)
        _save_json(_registry_path(), reg)
    return {"status": "removed", **SAFETY}


# ─── SIMULATED SOURCE ───────────────────────────────────────────

def create_simulated_eeg_source(source_id="simulated_eeg", sampling_rate_hz=250, n_channels=8):
    return register_biosignal_source({
        "source_id": source_id, "source_type": "simulated",
        "sampling_rate_hz": sampling_rate_hz, "n_channels": n_channels,
        "channel_names": ["Fz", "Cz", "Pz", "Oz", "F3", "F4", "P3", "P4"][:n_channels],
        "enabled": True, "raw_recording_enabled": False, "safe_public_export": False,
    })


def read_simulated_window(source_id="simulated_eeg", seconds=1.0):
    cfg = get_biosignal_source(source_id)
    if not cfg:
        return {"error": "source_not_found", **SAFETY}
    sr = cfg.get("sampling_rate_hz", 250)
    nc = cfg.get("n_channels", 8)
    n = int(sr * seconds)
    ch_data = []
    for ch in range(nc):
        data = [math.sin(2 * math.pi * 10.0 * i / sr + ch * 0.7) * 0.4 +
                math.sin(2 * math.pi * 6.0 * i / sr + ch * 0.3) * 0.2 +
                random.gauss(0, 0.15) +
                (0.05 * math.sin(0.02 * i / sr) if ch == 0 else 0)
                for i in range(n)]
        if random.random() < 0.02:
            b = random.randint(0, n - 10)
            for j in range(b, min(b + 8, n)):
                data[j] += random.uniform(-2.0, 2.0)
        ch_data.append(data)

    mags = [sum(abs(x) for x in ch_data[j]) / n for j in range(nc)]
    p2p = [max(ch_data[j]) - min(ch_data[j]) for j in range(nc)]
    return {
        "source_id": source_id, "timestamp": datetime.now(timezone.utc).isoformat(),
        "sampling_rate_hz": sr, "n_channels": nc, "n_samples": n,
        "window_summary": {"mean_abs_amplitude": round(sum(mags) / nc, 4),
                            "peak_to_peak": round(max(p2p), 4),
                            "variance": round(sum(v ** 2 for v in mags) / nc, 6),
                            "estimated_alpha_power": round(random.uniform(0.15, 0.4), 3),
                            "estimated_theta_power": round(random.uniform(0.05, 0.2), 3),
                            "estimated_beta_power": round(random.uniform(0.05, 0.15), 3)},
        "raw_samples_included": False, "simulated_demo_signal": True, **SAFETY,
    }


# ─── LSL ADAPTER ────────────────────────────────────────────────

def discover_lsl_streams(timeout=2.0):
    try:
        import pylsl
        streams = pylsl.resolve_streams(timeout)
        return {"available": True, "n_streams": len(streams),
                "streams": [{"name": s.name(), "type": s.type(), "channels": s.channel_count()}
                            for s in streams], **SAFETY}
    except ImportError:
        return {"available": False, "reason": "pylsl_not_installed",
                "install_hint": "pip install pylsl", **SAFETY}


def connect_lsl_stream(stream_name=None, stream_type="EEG"):
    try:
        import pylsl
        streams = pylsl.resolve_streams(timeout=2.0)
        target = None
        for s in streams:
            if stream_name and s.name() == stream_name:
                target = s
                break
            if not stream_name:
                target = s
                break
        if not target:
            return {"available": False, "reason": "no_stream_found", **SAFETY}
        sid = f"lsl_{target.name().replace(' ', '_')}"
        cfg = register_biosignal_source({
            "source_id": sid, "source_type": "lsl",
            "sampling_rate_hz": int(target.nominal_srate()),
            "n_channels": target.channel_count(), "enabled": True,
        })
        return {"available": True, "source": cfg, **SAFETY}
    except ImportError:
        return {"available": False, "reason": "pylsl_not_installed", **SAFETY}


def read_lsl_window(source_id, seconds=1.0):
    try:
        import pylsl
        cfg = get_biosignal_source(source_id)
        if not cfg:
            return {"error": "source_not_found", **SAFETY}
        sts = pylsl.resolve_streams(timeout=1.0)
        if not sts:
            return {"error": "no_stream_available", **SAFETY}
        inlet = pylsl.StreamInlet(sts[0])
        n = int(cfg.get("sampling_rate_hz", 250) * seconds)
        samples, _ = inlet.pull_chunk(timeout=seconds + 0.5, max_samples=n)
        if not samples:
            return {"source_id": source_id, "n_samples": 0, "window_summary": {},
                    "raw_samples_included": False, **SAFETY}
        nc = len(samples[0])
        mags = [sum(abs(s[j]) for s in samples) / len(samples) for j in range(nc)]
        p2p = [max(s[j] for s in samples) - min(s[j] for s in samples) for j in range(nc)]
        return {"source_id": source_id, "n_samples": len(samples),
                "window_summary": {"mean_abs_amplitude": round(sum(mags) / nc, 4),
                                    "peak_to_peak": round(max(p2p), 4),
                                    "variance": round(sum(v ** 2 for v in mags) / nc, 6)},
                "raw_samples_included": False, **SAFETY}
    except ImportError:
        return {"available": False, "reason": "pylsl_not_installed", **SAFETY}


# ─── BRAINFLOW ADAPTER ──────────────────────────────────────────

def check_brainflow_available():
    try:
        import brainflow
        return {"available": True, "version": getattr(brainflow, "__version__", "unknown"), **SAFETY}
    except ImportError:
        return {"available": False, "reason": "brainflow_not_installed",
                "install_hint": "pip install brainflow", **SAFETY}


def list_supported_brainflow_boards():
    boards = [
        {"board_id": -1, "name": "Synthetic Board (simulated)", "hardware_required": False},
        {"board_id": 0, "name": "Cyton Board", "hardware_required": True},
        {"board_id": 2, "name": "Ganglion Board", "hardware_required": True},
    ]
    return {"boards": boards, **SAFETY}


def create_brainflow_source(board_id=-1, serial_port=None):
    bf = check_brainflow_available()
    if not bf["available"]:
        return bf
    sid = f"brainflow_{board_id}"
    return register_biosignal_source({
        "source_id": sid, "source_type": "brainflow",
        "sampling_rate_hz": 250, "n_channels": 8, "enabled": True,
        "board_id": board_id, "serial_port": serial_port,
    })


def read_brainflow_window(source_id, seconds=1.0):
    bf = check_brainflow_available()
    if not bf["available"]:
        return bf
    cfg = get_biosignal_source(source_id)
    if not cfg:
        return {"error": "source_not_found", **SAFETY}
    try:
        import brainflow
        params = brainflow.BrainFlowInputParams()
        if cfg.get("serial_port"):
            params.serial_port = cfg["serial_port"]
        board = brainflow.BoardShim(cfg.get("board_id", -1), params)
        board.prepare_session()
        board.start_stream(45000)
        import time as _time
        _time.sleep(seconds)
        data = board.get_board_data()
        board.stop_stream()
        board.release_session()
        if data.size == 0:
            return {"source_id": source_id, "n_samples": 0, "window_summary": {},
                    "raw_samples_included": False, **SAFETY}
        nc = min(data.shape[0] - 1, 8)
        ch_data = [data[i] for i in range(nc)]
        mags = [float(abs(ch_data[j]).mean()) for j in range(nc)]
        return {"source_id": source_id, "n_samples": int(data.shape[1]),
                "window_summary": {"mean_abs_amplitude": round(sum(mags) / nc, 4),
                                    "peak_to_peak": 0.0, "variance": 0.0},
                "raw_samples_included": False, **SAFETY}
    except Exception as e:
        return {"error": str(e), **SAFETY}


# ─── SIGNAL QUALITY ─────────────────────────────────────────────

def compute_signal_quality(window_summary, source_metadata=None):
    if not window_summary:
        return {"overall_sqi": 0.5, "quality_state": "usable",
                "warnings": ["no_data"], **SAFETY}
    ws = window_summary
    var = ws.get("variance", 0)
    p2p = ws.get("peak_to_peak", 0)
    score = 1.0
    warnings = []
    if var < 1e-8:
        score -= 0.4
        warnings.append("flatline_risk")
    elif var < 1e-6:
        score -= 0.15
        warnings.append("low_variance")
    if p2p > 5.0:
        score -= 0.2
        warnings.append("saturation_risk")
    beta = ws.get("estimated_beta_power", 0)
    if beta > 0.3:
        score -= 0.1
        warnings.append("high_noise_risk")
    sqi = round(max(0.05, min(0.99, score)), 3)
    state = "excellent" if sqi > 0.85 else "good" if sqi > 0.7 else "usable" if sqi > 0.5 else "poor" if sqi > 0.25 else "unusable"
    return {"overall_sqi": sqi, "quality_state": state,
            "channel_quality": [{"channel": "ch1", "sqi": sqi}],
            "warnings": warnings,
            "safe_to_use_for_exploratory_feedback": sqi >= 0.55,
            "interpretation": "Signal quality engineering summary only. Not neural decoding, diagnosis, or validated neurofeedback.",
            **SAFETY}


# ─── MARKER SYNC ────────────────────────────────────────────────

def _marker_dir(marker_session_id):
    return os.path.join(BASE, "marker_sessions", marker_session_id)


def create_marker_session(guided_session_id, source_id=None):
    msid = str(uuid4())
    m = {"marker_session_id": msid, "guided_session_id": guided_session_id,
         "source_id": source_id, "started_at": datetime.now(timezone.utc).isoformat(),
         "status": "active", **SAFETY}
    d = _marker_dir(msid)
    _save_json(os.path.join(d, "manifest.json"), m)
    return m


def record_marker(marker_session_id, event_type, payload=None):
    d = _marker_dir(marker_session_id)
    m = _load_json(os.path.join(d, "manifest.json"))
    if not m:
        return {"error": "session_not_found", **SAFETY}
    marker = {"timestamp": datetime.now(timezone.utc).isoformat(), "event_type": event_type,
              "payload": payload or {}, **SAFETY}
    _append_jsonl(os.path.join(d, "markers.jsonl"), marker)
    return marker


def list_markers(marker_session_id):
    p = os.path.join(_marker_dir(marker_session_id), "markers.jsonl")
    if not os.path.exists(p):
        return []
    return [json.loads(line) for line in open(p) if line.strip()]


def close_marker_session(marker_session_id):
    d = _marker_dir(marker_session_id)
    m = _load_json(os.path.join(d, "manifest.json"))
    if m:
        m["status"] = "closed"
        _save_json(os.path.join(d, "manifest.json"), m)
    return m


# ─── MONITOR ────────────────────────────────────────────────────

def _monitor_dir(monitor_id):
    return os.path.join(BASE, "monitors", monitor_id)


def start_biosignal_monitor_for_guided_session(guided_session_id, source_id="simulated_eeg"):
    mid = str(uuid4())
    m = {"monitor_id": mid, "guided_session_id": guided_session_id, "source_id": source_id,
         "started_at": datetime.now(timezone.utc).isoformat(), "status": "active",
         "n_samples": 0, **SAFETY}
    d = _monitor_dir(mid)
    _save_json(os.path.join(d, "manifest.json"), m)
    return m


def sample_biosignal_monitor(monitor_id):
    d = _monitor_dir(monitor_id)
    m = _load_json(os.path.join(d, "manifest.json"))
    if not m:
        return {"error": "monitor_not_found", **SAFETY}
    window = read_simulated_window(m.get("source_id", "simulated_eeg"))
    sq = compute_signal_quality(window.get("window_summary", {}))
    sample = {"timestamp": datetime.now(timezone.utc).isoformat(),
              "source_id": m["source_id"], "window_summary": window.get("window_summary", {}),
              "signal_quality": sq, "raw_samples_included": False, **SAFETY}
    _append_jsonl(os.path.join(d, "derived_samples.jsonl"), sample)
    m["n_samples"] = m.get("n_samples", 0) + 1
    _save_json(os.path.join(d, "manifest.json"), m)
    return sample


def stop_biosignal_monitor(monitor_id):
    d = _monitor_dir(monitor_id)
    m = _load_json(os.path.join(d, "manifest.json"))
    if m:
        m["status"] = "stopped"
        m["stopped_at"] = datetime.now(timezone.utc).isoformat()
        _save_json(os.path.join(d, "manifest.json"), m)
        samples = [json.loads(line) for line in
                   open(os.path.join(d, "derived_samples.jsonl")) if line.strip()] if os.path.exists(os.path.join(d, "derived_samples.jsonl")) else []
        sqis = [s.get("signal_quality", {}).get("overall_sqi", 0.5) for s in samples]
        summ = {"monitor_id": monitor_id, "n_derived_samples": len(samples),
                "avg_sqi": round(sum(sqis) / max(len(sqis), 1), 3) if sqis else 0.5,
                "quality_state_distribution": {},
                "raw_eeg_included": False, **SAFETY}
        _save_json(os.path.join(d, "summary.json"), summ)
        return summ
    return {"error": "monitor_not_found", **SAFETY}


def get_biosignal_monitor_summary(monitor_id):
    p = os.path.join(_monitor_dir(monitor_id), "summary.json")
    return _load_json(p)


# ─── BIOSIGNAL REPORT ───────────────────────────────────────────

def build_biosignal_session_report(guided_session_id):
    from app.core.imagery.guided_session_runtime import get_guided_session
    gs = get_guided_session(guided_session_id)
    if not gs:
        return {"error": "session_not_found", **SAFETY}
    mid = gs.get("biosignal_monitor_id")
    summ = get_biosignal_monitor_summary(mid) if mid else None
    if not summ:
        return {"guided_session_id": guided_session_id, "has_biosignal_monitor": False,
                "raw_eeg_included": False, **SAFETY}
    report = {"guided_session_id": guided_session_id, "source_id": gs.get("biosignal_source_id"),
              "source_type": "simulated", "avg_sqi": summ.get("avg_sqi"),
              "n_derived_samples": summ.get("n_derived_samples", 0),
              "quality_state_distribution": summ.get("quality_state_distribution", {}),
              "artifact_warnings": [], "raw_eeg_included": False,
              "interpretation": "Signal quality engineering summary only. Not neural decoding.",
              **SAFETY}
    d = os.path.join(BASE, "reports")
    _save_json(os.path.join(d, f"{guided_session_id}_biosignal_report.json"), report)
    return report
