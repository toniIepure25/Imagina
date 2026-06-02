"""V24 SDK Standard — Integration Test."""

import os
import sys

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "imagina")


def main():
    print("=== V24 IMAGINA BENCHMARK SDK ===\n")
    user_id = "v24_test"

    from app.core.imagery.protocol_sdk import (
        build_reproducibility_manifest,
        export_protocol_to_sdk_format,
        get_external_protocol_schema,
        get_protocol_sdk_example,
        import_external_protocol,
        save_protocol_sdk_file,
        validate_benchmark_export_pack,
        validate_external_protocol,
    )

    schema = get_external_protocol_schema()
    assert schema["imagina_protocol_version"] == "1.0"
    print(f"1. Schema version: {schema['imagina_protocol_version']}")

    example = get_protocol_sdk_example()
    assert example["title"] is not None
    print(f"2. Example: {example['title']}")

    valid = validate_external_protocol(example)
    assert valid["quality_score"] >= 75, f"Score {valid['quality_score']} < 75"
    print(f"3. Validation: score={valid['quality_score']}, valid={valid['valid']}")

    bad = dict(example)
    bad["title"] = "Clinical Diagnosis Protocol"
    bad["boundaries"] = {"not_clinical": False}
    bad_res = validate_external_protocol(bad)
    assert not bad_res["valid"]
    assert len(bad_res["forbidden_terms_found"]) > 0
    print(f"4. Bad protocol rejected: forbidden={bad_res['forbidden_terms_found']}")

    imp = import_external_protocol(user_id, protocol_payload=example)
    assert imp.get("protocol_id") is not None
    pid = imp["protocol_id"]
    print(f"5. Imported: {pid[:12]}...")

    exp = export_protocol_to_sdk_format(pid)
    assert exp.get("target_dimensions") == ["vividness", "stability", "color_control"]
    print("6. Export roundtrip: OK")

    saved = save_protocol_sdk_file(pid)
    assert os.path.exists(saved["file_path"])
    print(f"7. Saved to file: {saved['file_path'][-30:]}")

    from app.core.imagery.protocol_studio import (
        analyze_protocol_run,
        complete_protocol_block,
        complete_protocol_run,
        export_imagina_benchmark_pack,
        start_next_protocol_block,
        start_protocol_run,
    )
    run = start_protocol_run(user_id, pid)
    rid = run["run_id"]
    from app.core.imagery.guided_session_runtime import complete_guided_session, submit_guided_micro_checkin
    session_ids = []
    for i in range(2):
        blk = start_next_protocol_block(rid)
        sid = blk.get("session", {}).get("session_id", "")
        if sid:
            submit_guided_micro_checkin(sid, {"vividness": 7, "stability": 6, "effort": 3, "fatigue": 2, "confidence": 8, "discomfort": 1})
            complete_guided_session(sid)
            complete_protocol_block(rid, sid)
            session_ids.append(sid)
    complete_protocol_run(rid)
    analyze_protocol_run(rid)
    exp_pack = export_imagina_benchmark_pack(user_id, rid)
    print(f"8. Run completed: {len(session_ids)} sessions, export={exp_pack['n_files']} files")

    manifest = build_reproducibility_manifest(user_id, pid, rid)
    assert manifest.get("protocol_hash") is not None
    print(f"9. Manifest: hash={manifest['protocol_hash']}")

    pack_valid = validate_benchmark_export_pack(exp_pack["export_dir"])
    assert pack_valid["valid_pack"]
    print("10. Pack validated: OK")

    from app.core.imagery.demo_data_seeder import build_portfolio_safe_summary, seed_imagina_demo_user
    demo = seed_imagina_demo_user("v24_demo", reset_existing=True)
    assert demo.get("created_run_id") is not None
    print(f"11. Demo seeded: {demo['created_sessions']}")

    summary = build_portfolio_safe_summary("v24_demo")
    assert summary.get("title") is not None
    print("12. Portfolio summary: generated")

    raw_eeg_ok = True
    for f in exp_pack.get("files", []):
        if os.path.exists(f):
            c = open(f, errors="ignore").read().lower()
            if "raw_eeg" in c:
                raw_eeg_ok = False
    assert raw_eeg_ok, "Raw EEG found in export"
    print("13. No raw EEG in export: OK")

    assert valid.get("not_clinical") is True
    assert manifest.get("not_bci_claim") is True
    assert demo.get("not_mind_reading") is True
    print("14. Safety flags: All OK")

    print("\n=== V24 IMAGINA BENCHMARK SDK: ALL TESTS PASSED ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
