"""IMAGINA V27 — API Smoke Test."""

import json
import sys
import urllib.error
import urllib.request


def _get(url):
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except Exception as e:
        return None, str(e)


def _post(url, data=None):
    req = urllib.request.Request(url, data=json.dumps(data or {}).encode(),
                                  headers={"Content-Type": "application/json"},
                                  method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except Exception as e:
        return None, str(e)


def main():
    base = sys.argv[2] if len(sys.argv) > 2 and sys.argv[1] == "--base-url" else "http://localhost:8000"
    seed = "--seed-demo" in sys.argv and sys.argv[sys.argv.index("--seed-demo") + 1] == "true" if "--seed-demo" in sys.argv else False

    checks, failures = [], []
    def check(name, status, expected=200):
        ok = status is not None and 200 <= status < 400
        checks.append({"name": name, "passed": ok, "status": status})
        if not ok:
            failures.append(f"{name}: status={status}")

    s, _ = _get(f"{base}/api/imagina/system/health")
    check("system_health", s)

    s, _ = _get(f"{base}/api/imagina/sdk/schema")
    check("sdk_schema", s)

    s, body = _get(f"{base}/api/imagina/sdk/example")
    check("sdk_example", s)
    if s and 200 <= s < 400:
        ex = json.loads(body)
        status, _ = _post(f"{base}/api/imagina/sdk/validate", ex)
        check("sdk_validate", status)

    if seed:
        status, _ = _post(f"{base}/api/imagina/demo/demo_user/seed")
        check("demo_seed", status)
        status, _ = _post(f"{base}/api/imagina/showcase/demo_user/build")
        check("showcase_build", status)
        status, _ = _get(f"{base}/api/imagina/showcase/demo_user")
        check("showcase_get", status)

    status, _ = _post(f"{base}/api/imagina/release/health")
    check("release_health", status)

    status, _ = _post(f"{base}/api/imagina/release/api-contract")
    check("api_contract", status)

    result = {"smoke_test_id": "api_smoke", "base_url": base,
              "passed": len(failures) == 0, "n_checks": len(checks),
              "checks": checks, "failures": failures}
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
