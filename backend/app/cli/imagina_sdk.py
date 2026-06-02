"""IMAGINA V24 — SDK CLI (one-command operations)."""

import sys


def cmd_schema():
    import json

    from app.core.imagery.protocol_sdk import get_external_protocol_schema
    print(json.dumps(get_external_protocol_schema(), indent=2, default=str))
    return 0

def cmd_example():
    import json
    import os

    from app.core.imagery.protocol_sdk import get_protocol_sdk_example
    data = get_protocol_sdk_example()
    out = sys.argv[3] if len(sys.argv) > 3 and sys.argv[2] == "--output" else None
    if out:
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w") as f:
            json.dump(data, f, indent=2, default=str)
        print(f"Example saved to {out}")
    else:
        print(json.dumps(data, indent=2, default=str))
    return 0

def cmd_validate():
    import json
    path = None
    for i, a in enumerate(sys.argv):
        if a == "--file" and i + 1 < len(sys.argv):
            path = sys.argv[i + 1]
    if not path:
        print("Usage: python3 -m app.cli.imagina_sdk validate --file path/to/protocol.json")
        return 1
    with open(path) as f:
        payload = json.load(f)
    from app.core.imagery.protocol_sdk import validate_external_protocol
    result = validate_external_protocol(payload)
    print(json.dumps(result, indent=2, default=str))
    return 0 if result["valid"] else 1

def cmd_import():
    import json
    user = "default"
    path = None
    for i, a in enumerate(sys.argv):
        if a == "--user" and i + 1 < len(sys.argv):
            user = sys.argv[i + 1]
        if a == "--file" and i + 1 < len(sys.argv):
            path = sys.argv[i + 1]
    if not path:
        print("Usage: ... imagina_sdk import --user default --file path/to/protocol.json")
        return 1
    with open(path) as f:
        payload = json.load(f)
    from app.core.imagery.protocol_sdk import import_external_protocol
    r = import_external_protocol(user, file_path=path, protocol_payload=payload)
    print(json.dumps(r, indent=2, default=str))
    return 0 if not r.get("error") else 1

def cmd_export_protocol():
    import json
    pid = None
    for i, a in enumerate(sys.argv):
        if a == "--protocol-id" and i + 1 < len(sys.argv):
            pid = sys.argv[i + 1]
    if not pid:
        print("Usage: ... imagina_sdk export-protocol --protocol-id <id>")
        return 1
    from app.core.imagery.protocol_sdk import save_protocol_sdk_file
    r = save_protocol_sdk_file(pid)
    print(json.dumps(r, indent=2, default=str))
    return 0 if not r.get("error") else 1

def cmd_demo():
    import json
    user = "demo_user"
    for i, a in enumerate(sys.argv):
        if a == "--user" and i + 1 < len(sys.argv):
            user = sys.argv[i + 1]
    from app.core.imagery.demo_data_seeder import seed_imagina_demo_user
    r = seed_imagina_demo_user(user)
    print(json.dumps(r, indent=2, default=str))
    return 0

def cmd_manifest():
    import json
    user = "default"
    rid = None
    for i, a in enumerate(sys.argv):
        if a == "--user" and i + 1 < len(sys.argv):
            user = sys.argv[i + 1]
        if a == "--run-id" and i + 1 < len(sys.argv):
            rid = sys.argv[i + 1]
    from app.core.imagery.protocol_sdk import build_reproducibility_manifest
    r = build_reproducibility_manifest(user, run_id=rid)
    print(json.dumps(r, indent=2, default=str))
    return 0

def cmd_benchmark_export():
    import json
    user = "default"
    rid = None
    for i, a in enumerate(sys.argv):
        if a == "--user" and i + 1 < len(sys.argv):
            user = sys.argv[i + 1]
        if a == "--run-id" and i + 1 < len(sys.argv):
            rid = sys.argv[i + 1]
    from app.core.imagery.protocol_studio import export_imagina_benchmark_pack
    r = export_imagina_benchmark_pack(user, rid)
    print(json.dumps(r, indent=2, default=str))
    return 0

def main():
    if len(sys.argv) < 2:
        print("IMAGINA Benchmark SDK CLI")
        print("  schema | example | validate --file <path> | import --user <id> --file <path>")
        print("  export-protocol --protocol-id <id> | demo [--user <id>]")
        print("  manifest --user <id> [--run-id <id>] | benchmark-export --user <id> [--run-id <id>]")
        return 0
    cmd = sys.argv[1]
    cmds = {"schema": cmd_schema, "example": cmd_example, "validate": cmd_validate,
            "import": cmd_import, "export-protocol": cmd_export_protocol,
            "demo": cmd_demo, "manifest": cmd_manifest, "benchmark-export": cmd_benchmark_export}
    if cmd in cmds:
        return cmds[cmd]()
    print(f"Unknown command: {cmd}")
    return 1

if __name__ == "__main__":
    sys.exit(main())
