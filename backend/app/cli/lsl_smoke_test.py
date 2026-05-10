import argparse
import asyncio
import importlib.util
import json
import os
import sys
from datetime import datetime, timezone

from app.signals.lsl_real_provider import RealLSLProvider

DISCLAIMER = (
    "This is an experimental local LSL smoke test. "
    "It does not diagnose, decode thoughts or dreams, provide clinical neurofeedback, "
    "or clinically validate EEG biomarkers. "
    "Outputs are derived proxy features for engineering validation only."
)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python3 -m app.cli.lsl_smoke_test",
        description="IMAGINA real LSL hardware smoke test — experimental validation only.",
    )
    p.add_argument("--windows", type=int, default=3, help="Number of EEG windows to collect (default: 3)")
    p.add_argument("--stream-name", type=str, default=None, help="Target LSL stream by name")
    p.add_argument(
        "--output", type=str, default=None,
        help="Output JSON path (default: data/exports/lsl_smoke_<ts>.json)",
    )
    p.add_argument("--overwrite", action="store_true", help="Allow overwriting existing output file")
    p.add_argument("--timeout", type=int, default=5, help="Stream discovery timeout in seconds (default: 5)")
    p.add_argument("--allow-experimental", action="store_true", help="Acknowledge this is an experimental LSL test")
    return p


def run_smoke_test(args: argparse.Namespace) -> dict:
    return asyncio.run(_run_smoke_test_async(args))


async def _run_smoke_test_async(args: argparse.Namespace) -> dict:
    from app.core.config import settings

    report: dict = {
        "tool": "imagina_lsl_smoke_test",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "disclaimer": DISCLAIMER,
        "experimental_enabled": bool(settings.enable_experimental_lsl),
        "provider_metadata": None,
        "initial_health": None,
        "final_health": None,
        "selected_stream": None,
        "windows_requested": args.windows,
        "windows_collected": 0,
        "feature_summaries": [],
        "warnings": [],
        "errors": [],
    }

    if not (args.allow_experimental or settings.enable_experimental_lsl):
        report["errors"].append(
            "Experimental LSL is not enabled. "
            "Use --allow-experimental or set IMAGINA_ENABLE_EXPERIMENTAL_LSL=true."
        )
        return report

    if not importlib.util.find_spec("pylsl"):
        report["errors"].append("pylsl is not installed. Install backend[lsl] to enable LSL integration.")
        return report

    provider = RealLSLProvider()
    report["provider_metadata"] = provider.metadata()
    report["initial_health"] = provider.health()

    streams = provider.discover_streams()
    if not streams:
        report["errors"].append(
            "No LSL streams found. "
            "Ensure a stream is active (e.g. Muse, OpenBCI, or an LSL signal generator)."
        )
        return report

    selected = None
    if args.stream_name:
        for s in streams:
            if s["name"] == args.stream_name:
                selected = s
                break
        if not selected:
            report["errors"].append(f"Stream '{args.stream_name}' not found. Available: {[s['name'] for s in streams]}")
            return report
    else:
        selected = streams[0]
    report["selected_stream"] = selected

    try:
        await provider.start("lsl_smoke_test", stream_name=selected["name"])
    except Exception as e:
        report["errors"].append(f"Failed to start LSL session: {e}")
        return report

    for i in range(args.windows):
        try:
            fv = await provider.next_window("lsl_smoke_test", i, total_windows=args.windows)
            report["windows_collected"] += 1
            report["feature_summaries"].append({
                "window_index": i,
                "real_signal": fv.real_signal,
                "provider_id": fv.provider_id,
                "provider_type": fv.provider_type,
                "theta_power": fv.theta_power,
                "alpha_power": fv.alpha_power,
                "beta_power": fv.beta_power,
                "theta_beta_ratio": fv.theta_beta_ratio,
                "alpha_stability": fv.alpha_stability,
                "signal_quality": fv.signal_quality,
                "behavioral_stability": fv.behavioral_stability,
                "simulated_imagery_strength": fv.simulated_imagery_strength,
                "blink_score": fv.blink_score,
                "muscle_score": fv.muscle_score,
                "drift_score": fv.drift_score,
                "clipping_score": fv.clipping_score,
                "missing_data_ratio": fv.missing_data_ratio,
                "artifact_flags": fv.artifact_flags,
                "channel_count": fv.channel_count,
                "sampling_rate_hz": fv.sampling_rate_hz,
                "channels_used": fv.channels_used,
                "preprocessing_version": fv.preprocessing_version,
                "feature_version": fv.feature_version,
                "raw_persisted": False,
            })
        except Exception as e:
            report["errors"].append(f"Window {i} failed: {e}")
            break

    try:
        await provider.stop("lsl_smoke_test")
    except Exception:
        pass
    report["final_health"] = provider.health()
    return report


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not (args.allow_experimental or _get_experimental_enabled()):
        print(DISCLAIMER, file=sys.stderr)
        print("Error: Experimental LSL is not enabled.", file=sys.stderr)
        print("Use --allow-experimental or set IMAGINA_ENABLE_EXPERIMENTAL_LSL=true.", file=sys.stderr)
        return 2

    print(DISCLAIMER, file=sys.stderr)

    if not importlib.util.find_spec("pylsl"):
        print("Error: pylsl is not installed. Install via: pip install -e '.[lsl]'", file=sys.stderr)
        return 3

    report = run_smoke_test(args)
    _print_summary(report)

    output_path = args.output or _default_output_path()
    output = _resolve_output_path(output_path, args.overwrite)
    if output is None:
        print(f"Error: Output file exists: {output_path}. Use --overwrite to replace.", file=sys.stderr)
        return 1

    with open(output, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"Smoke report written to {output}", file=sys.stderr)

    if report["errors"]:
        first_error = str(report["errors"][0]).lower()
        if "stream" in first_error or "pylsl" in first_error:
            return 3
        return 1
    return 0


def _get_experimental_enabled() -> bool:
    try:
        from app.core.config import settings
        return bool(settings.enable_experimental_lsl)
    except Exception:
        return False


def _default_output_path() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    base = os.path.join(os.path.dirname(__file__), "..", "..", "data", "exports")
    return os.path.abspath(os.path.join(base, f"lsl_smoke_test_{ts}.json"))


def _resolve_output_path(path: str, overwrite: bool) -> str | None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not overwrite and os.path.exists(path):
        return None
    return path


def _print_summary(report: dict) -> None:
    print(file=sys.stderr)
    print("--- LSL Smoke Test Results ---", file=sys.stderr)
    print(f"  Pylsl installed: {'Yes' if report.get('pylsl_installed') else 'N/A'}", file=sys.stderr)
    stream = report.get("selected_stream")
    if stream:
        print(
            f"  Stream: {stream['name']} ({stream['type']}) | "
            f"{stream['channel_count']}ch @ {stream['nominal_srate']}Hz",
            file=sys.stderr,
        )
    print(f"  Windows: {report.get('windows_collected', 0)}/{report.get('windows_requested', 0)}", file=sys.stderr)
    for s in report.get("feature_summaries", []):
        print(
            f"    Win {s['window_index']}: alpha={s['alpha_power']:.3f} "
            f"theta={s['theta_power']:.3f} beta={s['beta_power']:.3f} "
            f"sq={s['signal_quality']:.3f}",
            file=sys.stderr,
        )
    for e in report.get("errors", []):
        print(f"  Error: {e}", file=sys.stderr)
    print("---", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
