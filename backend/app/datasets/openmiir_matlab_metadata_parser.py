"""OpenMIIR MATLAB Metadata Parser v3.9.4."""

import json
import os
import re
import sys
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
CANDIDATES_DIR = os.path.join(BASE, "..", "..", "data", "external", "openmiir", "meta", "github_candidates")
EXPORTS = os.path.join(BASE, "..", "..", "data", "exports")

EVENT_CODE_KEYWORDS = [
    "send_marker", "send_trigger", "trigger", "marker", "event_code",
    "event_id", "stim_code", "condition_code", "io64", "outp",
    "SendTrigger", "sendtrigger", "write_trigger",
    "parallel_port", "parallelport", "lpt",
]

CODE_PATTERN = re.compile(r'\b(1[0-4]|2[1-4]|3[0-4]|4[0-4]|'
                           r'11[0-4]|12[0-4]|13[0-4]|14[0-4]|'
                           r'21[0-4]|22[0-4]|23[0-4]|24[0-4]|'
                           r'1000|1111|2000|2001)\b')

CONDITION_PATTERN = re.compile(
    r'(perception|imagery|imagin|listen|perceiv|play|auditor)',
    re.IGNORECASE)


def _find_m_files():
    files = []
    if not os.path.isdir(CANDIDATES_DIR):
        return files
    for fn in os.listdir(CANDIDATES_DIR):
        if fn.lower().endswith(".m"):
            files.append(os.path.join(CANDIDATES_DIR, fn))
    return sorted(files)


def parse_matlab_script(path, original_name):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception:
        return None

    lines = content.splitlines()
    event_assignments = []
    condition_assignments = []
    trigger_calls = []
    switch_case_mappings = []
    comments_near_codes = []
    explicit_code_mappings = []

    in_switch = False
    switch_var = None

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("%"):
            continue

        code_matches = CODE_PATTERN.findall(stripped)
        has_code = len(code_matches) > 0
        has_condition = bool(CONDITION_PATTERN.search(stripped.lower()))
        has_trigger = any(kw in stripped.lower() for kw in EVENT_CODE_KEYWORDS)

        if has_code and has_trigger:
            event_assignments.append({
                "line": i + 1,
                "text": stripped[:300],
                "codes": [int(c) for c in code_matches],
                "context": _get_context(lines, i),
            })

        if has_code and has_condition:
            condition_assignments.append({
                "line": i + 1,
                "text": stripped[:300],
                "codes": [int(c) for c in code_matches],
                "condition_terms": CONDITION_PATTERN.findall(stripped.lower()),
            })

        if has_trigger:
            trigger_calls.append({
                "line": i + 1,
                "text": stripped[:300],
                "codes": [int(c) for c in code_matches] if has_code else [],
            })

        if re.match(r'switch\s', stripped.lower()):
            in_switch = True
            switch_var = stripped.split()[-1] if stripped.split() else "unknown"
        elif in_switch and re.match(r'case\s', stripped.lower()):
            case_val = stripped.split(None, 1)[1].strip() if len(stripped.split()) > 1 else "?"
            if has_code:
                switch_case_mappings.append({
                    "line": i + 1,
                    "switch_var": switch_var,
                    "case": case_val,
                    "codes": [int(c) for c in code_matches],
                    "text": stripped[:300],
                })
        elif in_switch and re.match(r'(otherwise|end)', stripped.lower()):
            in_switch = False
            switch_var = None

        if has_code:
            comment = _find_comment(lines, i)
            if comment:
                comments_near_codes.append({
                    "line": i + 1,
                    "code_line": stripped[:200],
                    "comment": comment,
                })

    explicit_code_mappings = [a for a in event_assignments if a.get("codes") and len(a["codes"]) >= 2]

    return {
        "file": original_name,
        "line_count": len(lines),
        "event_code_assignments": event_assignments[:30],
        "condition_assignments": condition_assignments[:20],
        "trigger_calls": trigger_calls[:20],
        "switch_case_mappings": switch_case_mappings,
        "comments_near_codes": comments_near_codes[:20],
        "explicit_code_mappings": explicit_code_mappings,
    }


def _get_context(lines, idx, window=2):
    start = max(0, idx - window)
    end = min(len(lines), idx + window + 1)
    return [lines[j].strip()[:200] for j in range(start, end) if not lines[j].strip().startswith("%")]


def _find_comment(lines, idx):
    line = lines[idx]
    if "%" in line:
        return line.split("%", 1)[1].strip()[:200]
    for j in range(max(0, idx - 3), idx):
        if lines[j].strip().startswith("%"):
            return lines[j].strip()[1:].strip()[:200]
    return None


def main():
    os.makedirs(EXPORTS, exist_ok=True)
    m_files = _find_m_files()
    files_parsed = 0
    all_data = []
    all_assignments = []
    all_condition_assignments = []
    all_switch_mappings = []
    all_explicit = []
    evidence_level = "none"

    for path in m_files:
        original = (os.path.basename(path).replace("_", "/", 1)
                   if "_" in os.path.basename(path)
                   else os.path.basename(path))
        result = parse_matlab_script(path, original)
        if result:
            files_parsed += 1
            all_data.append(result)
            all_assignments.extend(result.get("event_code_assignments", []))
            all_condition_assignments.extend(result.get("condition_assignments", []))
            all_switch_mappings.extend(result.get("switch_case_mappings", []))
            all_explicit.extend(result.get("explicit_code_mappings", []))

    if all_explicit or (all_condition_assignments and all_assignments):
        evidence_level = "weak_hypothesis"
    if all_switch_mappings and all_condition_assignments:
        evidence_level = "strong_hypothesis"

    report = {
        "tool": "openmiir_matlab_metadata_parser_v3.9.4",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "files_found": len(m_files),
        "files_parsed": files_parsed,
        "scripts": all_data,
        "event_code_assignments": all_assignments,
        "condition_assignments": all_condition_assignments,
        "trigger_calls": [t for t in all_assignments if t.get("codes")],
        "switch_case_mappings": all_switch_mappings,
        "comments_near_codes": [],
        "explicit_code_mappings": all_explicit,
        "evidence_level": evidence_level,
    }

    json_path = os.path.join(EXPORTS, "openmiir_matlab_metadata_index.json")
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    md_lines = [
        "# OpenMIIR MATLAB Metadata Index",
        f"**Files found**: {len(m_files)}",
        f"**Files parsed**: {files_parsed}",
        f"**Evidence level**: {evidence_level}",
        "",
        "## Event Code Assignments",
    ]
    for a in all_assignments[:15]:
        md_lines.append(f"- Line {a['line']}: `{a['text'][:120]}` (codes: {a.get('codes', [])})")

    md_lines.append("")
    md_lines.append("## Switch/Case Mappings")
    for s in all_switch_mappings[:15]:
        md_lines.append(f"- `{s['switch_var']}` case `{s['case']}`: `{s['text'][:120]}`")

    md_path = os.path.join(EXPORTS, "openmiir_matlab_metadata_index.md")
    with open(md_path, "w") as f:
        f.write("\n".join(md_lines))

    print(f"MATLAB parser: files_found={len(m_files)} parsed={files_parsed} "
          f"assignments={len(all_assignments)} evidence={evidence_level}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
