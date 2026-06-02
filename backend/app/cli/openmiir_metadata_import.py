"""OpenMIIR metadata importer v3.9.4 — expanded to download Excel/MATLAB/scripts."""

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
META_DIR = os.path.join(BASE, "..", "..", "data", "external", "openmiir", "meta")
EXPORTS = os.path.join(BASE, "..", "..", "data", "exports")
CANDIDATES_DIR = os.path.join(META_DIR, "github_candidates")
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

ALLOWED_EXTS = {".md", ".txt", ".csv", ".tsv", ".json", ".py", ".ipynb", ".yaml", ".yml",
                ".xlsx", ".xls", ".ods", ".m"}

HARD_SKIP = [
    "audio", ".wav", ".mp3", ".ogg", ".flac", ".aiff",
    ".fif", ".edf", ".bdf", ".vhdr", ".vmrk", ".set", ".fdt",
    ".npy", ".npz", ".pkl", ".joblib", ".h5",
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
    ".pt", ".pth", ".onnx", ".model",
]

SMALL_MAT_MAX = 5 * 1024 * 1024

SEARCH_TERMS = [
    "event", "events", "stim", "stimulus", "stimuli",
    "marker", "markers", "trigger", "trial", "condition",
    "perception", "imagery", "imagination", "listen", "listening",
    "audio", "onset", "response", "key",
    "1000", "1111", "2000", "2001",
]


def build_parser():
    import argparse
    p = argparse.ArgumentParser(prog="python3 -m app.cli.openmiir_metadata_import")
    p.add_argument("--dataset", default="openmiir")
    p.add_argument("--source", default="auto")
    p.add_argument("--force", action="store_true")
    p.add_argument("--include-binary-metadata", default="true")
    p.add_argument("--max-file-size-mb", type=int, default=10)
    return p


def _fetch_github_tree():
    branches = ["master", "main"]
    tree_entries = []
    valid_branch = None
    errors = []
    for branch in branches:
        try:
            url = f"https://api.github.com/repos/sstober/openmiir/git/trees/{branch}?recursive=1"
            req = urllib.request.Request(url, headers={"User-Agent": "IMAGINA/3.9"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
                tree_entries = data.get("tree", [])
                valid_branch = branch
                break
        except Exception as e:
            errors.append(f"GitHub tree {branch}: {e}")
    return tree_entries, valid_branch, errors


def _is_safe_download(entry, include_binary, max_size_mb):
    path = entry.get("path", "").lower()
    size = entry.get("size", 0)
    max_size = max_size_mb * 1024 * 1024
    if size is None or size > max_size:
        return False, "size_limit"
    ext = os.path.splitext(path)[1].lower()

    if any(skip in path for skip in HARD_SKIP):
        if ext == ".mat" and include_binary and (size or 0) <= SMALL_MAT_MAX:
            return True, "ok_small_mat"
        return False, "hard_skip"

    if ext in ALLOWED_EXTS:
        return True, "ok"

    if include_binary and ext in {".mat", ".xls", ".xlsx", ".ods", ".m"}:
        if size and size <= max_size:
            return True, "ok_binary_metadata"
        return False, "size_limit"

    return False, "ext_not_allowed"


def _download_candidate(url, dest_path):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "IMAGINA/3.9"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with open(dest_path, "wb") as f:
            f.write(data)
        return True, os.path.getsize(dest_path)
    except Exception as e:
        return False, str(e)


def _parse_content(filepath, ext):
    if ext in {".xlsx", ".xls", ".ods", ".mat"}:
        return ""
    try:
        if ext in {".ipynb"}:
            with open(filepath, "r", encoding="utf-8") as f:
                nb = json.load(f)
            lines = []
            for cell in nb.get("cells", []):
                lines.extend(cell.get("source", []))
            return "\n".join(lines)
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception:
        return ""


def _search_content(content, terms):
    matched = set()
    important_lines = []
    content_lower = content.lower()
    for term in terms:
        if term.lower() in content_lower:
            matched.add(term)
    for i, line in enumerate(content.splitlines(), 1):
        line_lower = line.lower()
        if len(line.strip()) < 3:
            continue
        for term in terms:
            if term in line_lower:
                important_lines.append({"line": i, "text": line.strip()[:200]})
                break
    if len(important_lines) > 50:
        important_lines = important_lines[:50]
    return sorted(matched), important_lines


def _inspect_stim_channels(manifest_path):
    stim_report = {
        "subjects": [],
        "subjects_with_stim": 0,
        "events_found": False,
        "unique_event_codes": [],
    }
    fif_files = []
    if os.path.exists(manifest_path):
        with open(manifest_path) as f:
            fif_files = json.load(f).get("files", [])[:10]
    for fif in fif_files:
        subj = os.path.splitext(os.path.basename(fif))[0]
        entry = {"subject": subj, "stim_channels": [], "n_events": 0, "event_codes": []}
        try:
            import mne
            raw = mne.io.read_raw_fif(fif, preload=False, verbose=False)
            for ch_name in raw.ch_names:
                idx = raw.ch_names.index(ch_name)
                ch_type = raw.get_channel_types(picks=[idx])[0]
                is_stim = (
                    "stim" in str(ch_type).lower() or "sti" in ch_name.lower()
                    or "status" in ch_name.lower() or "trigger" in ch_name.lower()
                    or "event" in ch_name.lower()
                )
                if is_stim:
                    entry["stim_channels"].append({"name": ch_name, "type": str(ch_type)})
            if entry["stim_channels"]:
                stim_report["subjects_with_stim"] += 1
                for sc in entry["stim_channels"]:
                    try:
                        events = mne.find_events(raw, stim_channel=sc["name"], shortest_event=1, verbose=False)
                        entry["n_events"] = len(events) if events is not None else 0
                        if len(events) > 0:
                            codes = {int(ev[2]) for ev in events}
                            entry["event_codes"] = sorted(codes)
                            stim_report["events_found"] = True
                            for c in codes:
                                if c not in stim_report["unique_event_codes"]:
                                    stim_report["unique_event_codes"].append(c)
                    except Exception:
                        pass
        except Exception as e:
            entry["error"] = str(e)
        stim_report["subjects"].append(entry)
    stim_report["unique_event_codes"] = sorted(stim_report["unique_event_codes"])
    return stim_report


def main(argv=None):
    args = build_parser().parse_args(argv)
    include_binary = args.include_binary_metadata.lower() in ("true", "1", "yes")
    max_size_mb = args.max_file_size_mb
    os.makedirs(META_DIR, exist_ok=True)
    os.makedirs(CANDIDATES_DIR, exist_ok=True)

    tree_entries, valid_branch, gh_errors = _fetch_github_tree()

    tree_inventory_path = os.path.join(META_DIR, "github_tree_inventory.json")
    with open(tree_inventory_path, "w") as f:
        json.dump({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "branch": valid_branch,
            "total_entries": len(tree_entries),
            "tree": tree_entries,
        }, f, indent=2, default=str)

    candidate_files = []
    xlsx_files = []
    matlab_files = []
    mat_files = []
    for item in tree_entries:
        path = item.get("path", "")
        name = path.lower()
        ext = os.path.splitext(path)[1].lower()

        if ext in {".xlsx", ".xls", ".ods"} and include_binary:
            xlsx_files.append({"path": path, "size": item.get("size"),
                                "url": f"https://raw.githubusercontent.com/sstober/openmiir/{valid_branch}/{path}"})

        if ext in {".m"} and include_binary:
            matlab_files.append({"path": path, "size": item.get("size"),
                                 "url": f"https://raw.githubusercontent.com/sstober/openmiir/{valid_branch}/{path}"})

        if ext in {".mat"} and include_binary:
            mat_files.append({"path": path, "size": item.get("size"),
                              "url": f"https://raw.githubusercontent.com/sstober/openmiir/{valid_branch}/{path}"})

        if any(kw in name for kw in (
            "meta", "trial", "event", "stim", "stimulus", "condition",
            "paradigm", "marker", "annotation", "design", "run",
            "session", "csv", "tsv", "json", "ipynb", "readme",
            "script", "presentation", "xlsx", "xls", "m",
        )):
            safe, reason = _is_safe_download(item, include_binary, max_size_mb)
            candidate_files.append({
                "path": path, "type": item.get("type"), "size": item.get("size"),
                "url": f"https://raw.githubusercontent.com/sstober/openmiir/{valid_branch}/{path}",
                "downloadable": safe, "skip_reason": None if safe else reason,
            })

    # Download all safe candidates
    content_index = []
    downloaded = []
    skipped = []
    for c in candidate_files:
        entry = {
            "path": c["path"], "downloaded": False, "size": c["size"],
            "matched_terms": [], "important_lines": [],
            "possible_mapping_evidence": False, "error": None,
        }
        if not c["downloadable"]:
            entry["error"] = c["skip_reason"]
            skipped.append(entry)
            content_index.append(entry)
            continue

        dest = os.path.join(CANDIDATES_DIR, c["path"].replace("/", "_"))
        success, result = _download_candidate(c["url"], dest)
        if not success:
            entry["error"] = str(result)[:200]
            skipped.append(entry)
            content_index.append(entry)
            continue

        entry["downloaded"] = True
        downloaded.append({"path": c["path"], "size": c["size"], "dest": dest})
        ext = os.path.splitext(c["path"])[1].lower()
        content = _parse_content(dest, ext)
        if content:
            matched, lines = _search_content(content, SEARCH_TERMS)
            entry["matched_terms"] = matched
            entry["important_lines"] = lines
            entry["possible_mapping_evidence"] = (
                len(matched) >= 2 or any(t in " ".join(matched) for t in ["1000", "2000", "condition", "event"]))
        content_index.append(entry)

    # Save download manifest
    xlsx_downloaded = [c for c in downloaded if any(c["path"].lower().endswith(e)
                       for e in (".xlsx", ".xls", ".ods"))]
    matlab_downloaded = [c for c in downloaded if c["path"].lower().endswith(".m")]
    mat_downloaded = [c for c in downloaded if c["path"].lower().endswith(".mat")]

    download_manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "downloaded_files": downloaded,
        "skipped_files": [s["path"] for s in skipped if s.get("error")],
        "xlsx_files": [x for x in xlsx_files if any(d["path"] == x["path"] for d in downloaded)],
        "matlab_files": [m for m in matlab_files if any(d["path"] == m["path"] for d in downloaded)],
        "mat_files": [m for m in mat_files if any(d["path"] == m["path"] for d in downloaded)],
        "candidate_count": len(candidate_files),
        "downloaded_count": len(downloaded),
    }
    with open(os.path.join(META_DIR, "download_manifest.json"), "w") as f:
        json.dump(download_manifest, f, indent=2, default=str)

    # Save indexes
    with open(os.path.join(META_DIR, "candidate_content_index.json"), "w") as f:
        json.dump({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_candidates": len(content_index),
            "downloaded_count": len(downloaded),
            "with_event_terms": sum(1 for c in content_index if c["matched_terms"]),
            "with_evidence": sum(1 for c in content_index if c["possible_mapping_evidence"]),
            "entries": content_index,
        }, f, indent=2, default=str)

    with open(os.path.join(META_DIR, "metadata_candidate_files.json"), "w") as f:
        json.dump({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_candidates": len(candidate_files),
            "downloadable_count": sum(1 for c in candidate_files if c["downloadable"]),
            "candidates": candidate_files,
        }, f, indent=2, default=str)

    # Stim inspection
    manifest_path = os.path.join(BASE, "..", "..", "data", "external", "openmiir", "manifest.json")
    stim_report = _inspect_stim_channels(manifest_path)

    files_with_evidence = [c["path"] for c in content_index if c["possible_mapping_evidence"]]

    report = {
        "tool": "openmiir_metadata_import_v3.9.4",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "github_branch": valid_branch,
        "github_tree_entries": len(tree_entries),
        "candidate_files_count": len(candidate_files),
        "downloaded_count": len(downloaded),
        "xlsx_files_found": len(xlsx_files),
        "xlsx_downloaded": len(xlsx_downloaded),
        "matlab_files_found": len(matlab_files),
        "matlab_downloaded": len(matlab_downloaded),
        "mat_files_found": len(mat_files),
        "mat_downloaded": len(mat_downloaded),
        "files_with_evidence": files_with_evidence,
        "stim_channel_inspection": stim_report,
        "condition_analysis_ready": False,
        "blocked_reason": "Semantic mapping unresolved. Hard metadata downloaded — parsing needed.",
        "disclaimer": "Experimental proxy features. Not clinical validation.",
    }

    with open(os.path.join(META_DIR, "metadata_discovery_report.json"), "w") as f:
        json.dump(report, f, indent=2, default=str)
    with open(os.path.join(EXPORTS, "openmiir_metadata_discovery.json"), "w") as f:
        json.dump(report, f, indent=2, default=str)
    with open(os.path.join(EXPORTS, "openmiir_stim_inventory.json"), "w") as f:
        json.dump(stim_report, f, indent=2, default=str)

    print(f"Metadata import v3.9.4: candidates={len(candidate_files)} "
          f"downloaded={len(downloaded)} xlsx={len(xlsx_downloaded)} "
          f"matlab={len(matlab_downloaded)} mat={len(mat_downloaded)} "
          f"stim_subs={stim_report['subjects_with_stim']} events={stim_report['events_found']}",
          file=sys.stderr)
    print(f"  XLSX: {[x['path'] for x in xlsx_downloaded]}", file=sys.stderr)
    print(f"  MATLAB: {[m['path'] for m in matlab_downloaded]}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
