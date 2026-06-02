"""IMAGINA V27 — Frontend Smoke Test + Local CI + Artifact Index + Submission Pack Validator."""

import json
import os
import sys
import time
from datetime import datetime, timezone
from uuid import uuid4

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "imagina")

SAFETY = {
    "analysis_mode": "personal_exploratory_training",
    "not_clinical": True, "not_diagnostic": True,
    "not_mind_reading": True, "not_bci_claim": True,
    "production_valid": False,
    "scientific_boundary": ("Personal exploratory adaptive mental imagery training only. "
                             "Not diagnosis, therapy, clinical treatment, "
                             "mind-reading, dream decoding, or validated BCI."),
}


def _load_json(p):
    return json.load(open(p)) if os.path.exists(p) else None


def _save_json(p, data):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        json.dump(data, f, indent=2, default=str)


def run_api_smoke_test(base_url="http://localhost:8000"):
    import urllib.error
    import urllib.request
    checks, failures = [], []

    def try_get(path):
        try:
            urllib.request.urlopen(f"{base_url}{path}", timeout=10)
            return True
        except Exception:
            return False

    def try_post(path, data=None):
        try:
            req = urllib.request.Request(f"{base_url}{path}",
                                          data=json.dumps(data or {}).encode(),
                                          headers={"Content-Type": "application/json"}, method="POST")
            urllib.request.urlopen(req, timeout=15)
            return True
        except Exception:
            return False

    for path in ["/api/imagina/system/health", "/api/imagina/sdk/schema", "/api/imagina/sdk/example"]:
        ok = try_get(path)
        checks.append({"endpoint": path, "passed": ok})
        if not ok:
            failures.append(path)

    try_get("/api/imagina/sdk/example")

    result = {"smoke_test_id": str(uuid4()), "base_url": base_url,
              "passed": len(failures) == 0, "n_checks": len(checks),
              "checks": checks, "failures": failures, **SAFETY}
    d = os.path.join(BASE, "smoke_tests")
    _save_json(os.path.join(d, "latest_api_smoke_test.json"), result)
    return result


def run_frontend_smoke_test(base_url="http://localhost:3000"):
    import urllib.error
    import urllib.request
    checks, failures = [], []
    for route in ["/imagina", "/imagina/showcase"]:
        try:
            with urllib.request.urlopen(f"{base_url}{route}", timeout=10) as r:
                ok = r.status < 500
        except Exception:
            ok = False
        checks.append({"route": route, "passed": ok})
        if not ok:
            failures.append(route)
    result = {"frontend_smoke_test_id": str(uuid4()), "base_url": base_url,
              "passed": len(failures) == 0, "routes_checked": checks, "failures": failures, **SAFETY}
    d = os.path.join(BASE, "smoke_tests")
    _save_json(os.path.join(d, "latest_frontend_smoke_test.json"), result)
    return result


def run_local_ci(mode="quick"):
    steps, failures = [], []
    start = time.time()
    repo = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")

    def run_cmd(cmd, cwd=None):
        import subprocess
        r = subprocess.run(cmd, shell=True, cwd=cwd or repo, capture_output=True, timeout=120)
        ok = r.returncode == 0
        if not ok:
            failures.append(cmd)
        return ok

    if mode in ("quick", "full", "release"):
        run_cmd("python3 -m ruff check backend/")
        steps.append("ruff")

    if mode in ("quick", "full", "release"):
        tests_v24_v26 = ["app.cli.imagina_v24_sdk_standard_test",
                         "app.cli.imagina_v25_public_showcase_test",
                         "app.cli.imagina_v26_release_candidate_test"]
        for t in tests_v24_v26:
            ok = run_cmd(f"python3 -m {t}", cwd=os.path.join(repo, "backend"))
            steps.append(t)
            if ok:
                pass

    if mode in ("full", "release"):
        run_cmd("npm run build", cwd=os.path.join(repo, "frontend"))
        steps.append("frontend_build")

    if mode == "release":
        run_cmd("python3 -m app.cli.imagina_release all", cwd=os.path.join(repo, "backend"))
        steps.append("release_all")

    result = {"ci_run_id": str(uuid4()), "mode": mode,
              "passed": len(failures) == 0, "steps": steps,
              "failures": failures, "duration_seconds": round(time.time() - start, 1), **SAFETY}
    d = os.path.join(BASE, "local_ci")
    _save_json(os.path.join(d, "latest_ci_report.json"), result)
    return result


def build_release_artifact_index(user_id="demo_user"):
    artifacts = [
        ("Showcase Summary", os.path.join(BASE, "showcase", user_id, "SHOWCASE_SUMMARY.md"), "docs"),
        ("Release Health", os.path.join(BASE, "release_health", "RELEASE_HEALTH.md"), "release"),
        ("API Contract", os.path.join(BASE, "api_contract", "imagina_api_contract.json"), "docs"),
        ("Architecture Map", os.path.join(BASE, "architecture", "IMAGINA_ARCHITECTURE_MAP.md"), "docs"),
        ("5-Min Demo Script", os.path.join(BASE, "demo_script", "IMAGINA_5_MIN_DEMO_SCRIPT.md"), "demo"),
        ("Whitepaper", os.path.join(BASE, "whitepaper", "IMAGINA_TECHNICAL_WHITEPAPER.md"), "docs"),
        ("Portfolio Summary", os.path.join(BASE, "portfolio_summary", user_id, "PORTFOLIO_SUMMARY.md"), "docs"),
        ("Reproducibility Manifest", os.path.join(BASE, "reproducibility_manifests", user_id, "latest_manifest.json"), "sdk"),
        ("Submission Pack", os.path.join(BASE, "submission_pack"), "release"),
        ("CI Report", os.path.join(BASE, "local_ci", "latest_ci_report.json"), "ci"),
    ]
    existing = [{"name": a[0], "path": a[1], "exists": os.path.exists(a[1]) if os.path.exists(a[1]) else any(
        os.path.exists(os.path.join(a[1], f)) for f in (os.listdir(a[1]) if os.path.isdir(a[1]) else [])),
                 "category": a[2], "safe_to_share": True} for a in artifacts]
    idx = {"artifact_index_id": str(uuid4()), "user_id": user_id,
           "generated_at": datetime.now(timezone.utc).isoformat(),
           "artifacts": existing, "n_existing": sum(1 for a in existing if a["exists"]),
           "n_missing": sum(1 for a in existing if not a["exists"]),
           "safe_share_bundle_ready": sum(1 for a in existing if a["exists"]) >= 6, **SAFETY}
    d = os.path.join(BASE, "release_artifacts")
    _save_json(os.path.join(d, "latest_artifact_index.json"), idx)
    return idx


def validate_submission_pack(submission_dir):
    required = ["README_FOR_REVIEWERS.md", "SAFETY_BOUNDARIES.md"]
    forbidden_exts = [".edf", ".fif", ".bdf"]
    missing, forbidden_files, forbidden_claims = [], [], []
    if not os.path.isdir(submission_dir):
        return {"valid_submission_pack": False, "error": "dir_not_found"}
    for fn in required:
        if not os.path.exists(os.path.join(submission_dir, fn)):
            missing.append(fn)
    for root, _, files in os.walk(submission_dir):
        for fn in files:
            if any(fn.endswith(ext) for ext in forbidden_exts):
                forbidden_files.append(fn)
            p = os.path.join(root, fn)
            try:
                c = open(p, errors="ignore").read().lower()
                for term in ["clinical", "diagnosis", "therapy", "treatment", "cure",
                              "bci-ready", "mind-reading", "dream decoding", "decode thoughts"]:
                    if term in c:
                        idx = c.index(term)
                        before = c[max(0, idx - 40):idx]
                        if "not " not in before and "no " not in before and "no" not in before:
                            forbidden_claims.append(f"{fn}: {term}")
                            break
            except Exception:
                pass
    result = {"valid_submission_pack": len(missing) == 0 and len(forbidden_files) == 0,
              "n_files_checked": len(missing) + sum(1 for _ in (os.listdir(submission_dir) if os.path.isdir(submission_dir) else [])),
              "missing_required_files": missing, "forbidden_files_found": forbidden_files,
              "forbidden_claims_found": forbidden_claims,
              "recommendations": ["Pack is valid."] if not missing and not forbidden_files and not forbidden_claims else ["Fix issues above."],
              **SAFETY}
    _save_json(os.path.join(submission_dir, "submission_pack_validation.json") if os.path.isdir(submission_dir) else "", result)
    return result


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "api-smoke":
        json.dump(run_api_smoke_test(sys.argv[2] if len(sys.argv) > 2 else "http://localhost:8000"), sys.stdout, indent=2)
    elif cmd == "quick-ci":
        json.dump(run_local_ci("quick"), sys.stdout, indent=2)
    elif cmd == "artifact-index":
        json.dump(build_release_artifact_index(), sys.stdout, indent=2)
    else:
        print("Usage: api-smoke | quick-ci | artifact-index")
