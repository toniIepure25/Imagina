"""OpenMIIR Candidate File Miner — Deep evidence extraction for event code semantics.

Parses downloaded GitHub repo files (.py, .ipynb, .md, .txt, .csv, .tsv, .json, .yaml)
and extracts: code mentions, variable assignments, dictionaries, tables, beat file structure,
and semantic keywords near event codes.
"""

import ast
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
CANDIDATES_DIR = os.path.join(BASE, "..", "..", "data", "external", "openmiir", "meta", "github_candidates")
EXPORTS = os.path.join(BASE, "..", "..", "data", "exports")
META_DIR = os.path.join(BASE, "..", "..", "data", "external", "openmiir", "meta")

SEMANTIC_KEYWORDS = [
    "perception", "perceive", "listening", "listen", "heard", "auditory", "sound", "audio", "playback",
    "imagery", "imagination", "imagine", "imagined", "mental", "covert", "think", "thought",
    "trial", "trials", "onset", "offset", "stimulus", "stimuli", "cue", "cues",
    "condition", "conditions", "block", "blocks", "session", "run",
    "response", "responses", "key", "press", "button", "reaction", "feedback",
    "beat", "beats", "beat_tracker", "downbeat", "rhythm", "tempo",
    "event", "events", "marker", "markers", "trigger", "triggers", "code",
    "label", "labels", "map", "mapping", "category", "categories", "class",
]

KNOWN_EVENT_CODES = set()
for r in [range(11, 45), range(111, 145), range(211, 245)]:
    for c in r:
        KNOWN_EVENT_CODES.add(c)
KNOWN_EVENT_CODES.update([1000, 1111, 2000, 2001])

CODE_PATTERN = re.compile(
    r'\b(1[0-4]|2[1-4]|3[0-4]|4[0-4]|'
    r'11[0-4]|12[0-4]|13[0-4]|14[0-4]|'
    r'21[0-4]|22[0-4]|23[0-4]|24[0-4]|'
    r'1000|1111|2000|2001)\b')
BEAT_FILE_PATTERN = re.compile(r'meta_beats\.(v[12])_(\d+)_(beats|cue_beats)\.txt')


def load_candidate_content_index():
    p = os.path.join(META_DIR, "candidate_content_index.json")
    if os.path.exists(p):
        with open(p) as f:
            return json.load(f)
    return None


def load_downloaded_candidate_files():
    files = {}
    if not os.path.isdir(CANDIDATES_DIR):
        return files
    for fn in os.listdir(CANDIDATES_DIR):
        path = os.path.join(CANDIDATES_DIR, fn)
        if os.path.isfile(path):
            files[fn] = path
    return files


def parse_beat_filename(filename):
    m = BEAT_FILE_PATTERN.search(filename)
    if m:
        return {
            "version": m.group(1),
            "code": int(m.group(2)),
            "file_type": m.group(3),
            "stimulus": int(m.group(2)[0]) if len(m.group(2)) > 1 else int(m.group(2)),
            "cue_type": int(m.group(2)[1]) if len(m.group(2)) > 1 else None,
        }
    return None


def parse_text_file(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception:
        return {"lines": [], "raw": ""}
    lines = content.splitlines()
    return {"lines": lines, "raw": content}


def parse_python_file(path):
    result = {"assignments": [], "dicts": [], "lists": [], "comments": [], "imports": []}
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            source = f.read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        name = target.id.lower()
                        if any(kw in name for kw in (
                            "event", "marker", "trigger", "stim", "stimulus",
                            "condition", "trial", "cue", "code", "label",
                            "onset", "response", "key", "beat",
                        )):
                            result["assignments"].append(_node_info(node, source))
            if isinstance(node, ast.Dict):
                keys = []
                for k in node.keys:
                    if isinstance(k, ast.Constant):
                        keys.append(k.value)
                if any(isinstance(k, int) and k in KNOWN_EVENT_CODES for k in keys):
                    result["dicts"].append(_node_info(node, source))
            if isinstance(node, ast.List):
                elts = []
                for e in node.elts:
                    if isinstance(e, ast.Constant):
                        elts.append(e.value)
                has_code = any(
                    (isinstance(e, int) and e in KNOWN_EVENT_CODES) for e in elts)
                if has_code:
                    result["lists"].append(_node_info(node, source))
            if isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                names = [alias.name for alias in node.names]
                result["imports"].append({"names": names, "lineno": node.lineno})
    except SyntaxError:
        pass
    except Exception:
        pass
    return result


def _node_info(node, source):
    try:
        snippet = ast.get_source_segment(source, node)
    except Exception:
        snippet = str(node)[:200]
    return {
        "lineno": getattr(node, "lineno", 0),
        "snippet": (snippet or "")[:300],
    }


def parse_notebook_file(path):
    result = {"cells": [], "code_evidence": []}
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            nb = json.load(f)
    except Exception:
        return result
    for i, cell in enumerate(nb.get("cells", [])):
        source = "".join(cell.get("source", []))
        cell_type = cell.get("cell_type", "")
        cell_info = {"index": i, "type": cell_type, "source": source[:500]}
        result["cells"].append(cell_info)
        if cell_type == "code" and any(kw in source.lower() for kw in SEMANTIC_KEYWORDS):
            result["code_evidence"].append(cell_info)
    return result


def extract_markdown_tables(lines):
    tables = []
    current_table = []
    in_table = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if "|" in stripped and stripped.count("|") >= 1:
            if not in_table:
                in_table = True
                current_table = [(i + 1, stripped)]
            else:
                current_table.append((i + 1, stripped))
        else:
            if in_table and len(current_table) >= 2:
                tables.append({"start_line": current_table[0][0], "rows": current_table})
            in_table = False
            current_table = []
    if in_table and len(current_table) >= 2:
        tables.append({"start_line": current_table[0][0], "rows": current_table})
    return tables


def extract_numeric_code_contexts(lines, filename):
    contexts = []
    for i, line in enumerate(lines):
        matches = CODE_PATTERN.findall(line)
        for code_str in matches:
            code = int(code_str)
            nearby = line[max(0, line.index(code_str) - 50):line.index(code_str) + len(code_str) + 50]
            nearby_lower = nearby.lower()
            matched_terms = [kw for kw in SEMANTIC_KEYWORDS if kw in nearby_lower]
            contexts.append({
                "code": code,
                "file": filename,
                "line": i + 1,
                "context": nearby.strip(),
                "nearby_terms": matched_terms,
                "confidence": "weak_hypothesis",
            })
    return contexts


def extract_beat_file_evidence(files):
    evidence = []
    beat_files = {}
    for fn, path in files.items():
        parsed = parse_beat_filename(fn)
        if parsed:
            beat_files[fn] = parsed

    stimuli = defaultdict(set)
    for fn, info in beat_files.items():
        stimuli[info["code"]].add(info["version"])

    for code in sorted(stimuli.keys()):
        versions = sorted(stimuli[code])
        evidence.append({
            "type": "beat_file_naming",
            "code": code,
            "evidence": f"Beat file exists for code {code} (versions: {versions})",
            "file_pattern": f"meta/beats.{{v}}/{code}_beats.txt",
            "interpretation": (
                f"Code {code} corresponds to a specific beat track. "
                f"Two-digit codes (11-44) map to stimulus×cue beat files."
            ),
            "confidence": "strong_hypothesis",
        })

    return evidence, beat_files


def extract_readme_evidence(lines, filename):
    evidence = []
    content = "\n".join(lines)
    content_lower = content.lower()

    if "listening to and imagining" in content_lower or "perception and imagination" in content_lower:
        evidence.append({
            "type": "readme_claim",
            "file": filename,
            "evidence": ("Dataset explicitly described as 'listening to and imagining' — "
                         "confirms perception + imagery conditions exist"),
            "quote": _find_sentence(content, ["listening", "imagining", "perception", "imagination"]),
            "confidence": "strong_hypothesis",
        })

    if "12 short music fragments" in content_lower:
        evidence.append({
            "type": "stimulus_count",
            "file": filename,
            "evidence": "12 short music fragments mentioned",
            "quote": _find_sentence(content, ["12 short music fragments"]),
            "confidence": "weak_hypothesis",
        })

    if "beats.v1" in content_lower or "beats.v2" in content_lower:
        evidence.append({
            "type": "beat_tracker_version",
            "file": filename,
            "evidence": "Beat files present for v1 (P01-P08) and v2 (P09-P14)",
            "quote": "beats.v1 - beat onsets in the stimuli and cues as detected by the librosa beat tracker",
            "confidence": "strong_hypothesis",
        })

    return evidence


def _find_sentence(text, keywords):
    sentences = re.split(r'[.!?]\s+', text)
    for s in sentences:
        if all(kw.lower() in s.lower() for kw in keywords):
            return s.strip()[:300]
    return None


def build_evidence_graph():
    files = load_downloaded_candidate_files()
    code_mentions = []
    extracted_mappings = []
    candidate_labels = defaultdict(list)
    file_evidence = {}
    beat_file_evidence = []
    readme_evidence = []
    files_analyzed = 0

    beat_evidence, beat_info = extract_beat_file_evidence(files)
    beat_file_evidence = beat_evidence
    for be in beat_evidence:
        candidate_labels[be["code"]].append(be)
        extracted_mappings.append({
            "source_file": f"meta/beats.*/{be['code']}_beats.txt",
            "mapping_type": "beat_file_naming",
            "mapping": {str(be["code"]): "Beat track for stimulus/cue"},
            "confidence": be["confidence"],
            "evidence_quote": be["evidence"],
            "reasoning": be["interpretation"],
        })

    for fn, path in sorted(files.items()):
        ext = os.path.splitext(fn)[1].lower()
        if ext not in {".md", ".txt", ".csv", ".tsv", ".json", ".py", ".ipynb", ".yaml", ".yml"}:
            continue
        files_analyzed += 1

        parsed = parse_text_file(path)
        lines = parsed.get("lines", [])

        if ext in {".py"}:
            py_info = parse_python_file(path)
            file_evidence[fn] = py_info

        if ext in {".ipynb"}:
            nb_info = parse_notebook_file(path)
            file_evidence[fn] = nb_info

        if ext in {".md", ".txt", ".csv", ".tsv"}:
            code_contexts = extract_numeric_code_contexts(lines, fn)
            code_mentions.extend(code_contexts)
            for cc in code_contexts:
                candidate_labels[cc["code"]].append({
                    "source": fn,
                    "line": cc["line"],
                    "context": cc["context"],
                    "terms": cc["nearby_terms"],
                })

            tables = extract_markdown_tables(lines)
            if tables:
                for t in tables:
                    rows_text = "\n".join(r[1] for r in t["rows"])
                    code_matches = CODE_PATTERN.findall(rows_text)
                    if code_matches:
                        extracted_mappings.append({
                            "source_file": fn,
                            "mapping_type": "markdown_table",
                            "mapping": raw_table_to_dict(t),
                            "confidence": "strong_hypothesis" if len(code_matches) >= 2 else "weak_hypothesis",
                            "evidence_quote": rows_text[:500],
                            "reasoning": (
                                f"Table in {fn} line {t['start_line']} "
                                f"has {len(code_matches)} code references"
                            ),
                        })

        if fn == "README.md" or fn == "meta_README.md":
            rev = extract_readme_evidence(lines, fn)
            readme_evidence.extend(rev)
            for r in rev:
                extracted_mappings.append({
                    "source_file": fn,
                    "mapping_type": "readme_claim",
                    "mapping": {"claim": r["evidence"]},
                    "confidence": r["confidence"],
                    "evidence_quote": r.get("quote", "") or r["evidence"],
                    "reasoning": r["evidence"],
                })

    confirmed = [m for m in extracted_mappings if m["confidence"] == "confirmed"]
    strong = [m for m in extracted_mappings if m["confidence"] == "strong_hypothesis"]
    weak = [m for m in extracted_mappings if m["confidence"] == "weak_hypothesis"]

    graph = {
        "tool": "openmiir_candidate_miner_v3.9.3",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "files_analyzed": files_analyzed,
        "total_downloaded": len(files),
        "files_with_numeric_codes": list(
            set(cc["file"] for cc in code_mentions)
        ),
        "files_with_condition_terms": [
            fn for fn, ev in file_evidence.items()
            if ev and (isinstance(ev, dict) and (ev.get("assignments") or ev.get("code_evidence")))
        ],
        "code_mentions": code_mentions,
        "extracted_mappings": extracted_mappings,
        "candidate_semantic_labels": {
            str(k): [{"source": li.get("source", li.get("file", "unknown")),
                       "context": str(li.get("context", li.get("evidence", "")))[:200]}
            for li in v]
            for k, v in candidate_labels.items()
        },
        "beat_file_structure": {
            "pattern": "{stimulus_digit}{cue_digit}_beats.txt",
            "stimuli": [1, 2, 3, 4],
            "cue_types": [1, 2, 3, 4],
            "versions": ["v1", "v2"],
            "v1_subjects": "P01-P08",
            "v2_subjects": "P09-P14",
        },
        "readme_evidence": readme_evidence,
        "beat_file_evidence": beat_file_evidence,
        "confirmed_code_mappings": {
            str(m.get("code", "unknown")): m
            for m in extracted_mappings if m["confidence"] == "confirmed"
        },
        "strong_hypothesis_mappings": {
            m.get("source_file", ""): m
            for m in strong
        },
        "weak_hypothesis_mappings": [
            m for m in weak
        ],
        "confidence_summary": {
            "confirmed": len(confirmed),
            "strong_hypothesis": len(strong),
            "weak_hypothesis": len(weak),
            "total_mentions": len(code_mentions),
        },
        "perception_imagery_confirmed": False,
        "perception_imagery_evidence": {
            "readme_confirms_both_conditions": any(
                r["evidence"].lower().find("perception") >= 0 and
                r["evidence"].lower().find("imag") >= 0
                for r in readme_evidence
            ),
            "no_explicit_code_to_condition_map": True,
            "note": (
                "README confirms perception and imagery conditions exist in dataset. "
                "Beat files map two-digit codes to specific stimulus×cue tracks. "
                "But NO explicit 11=perception or 21=imagery mapping found. "
                "The 100s-vs-200s code family distinction remains a structural hypothesis."
            ),
        },
    }

    return graph


def raw_table_to_dict(table):
    rows = table.get("rows", [])
    if len(rows) < 2:
        return {}
    headers = [c.strip() for c in rows[0][1].split("|") if c.strip()]
    if not headers:
        return {}
    result = {}
    for r in rows[1:]:
        cells = [c.strip() for c in r[1].split("|") if c.strip()]
        if len(cells) >= 2:
            key = cells[0]
            val = cells[1]
            try:
                key_int = int(key)
                result[str(key_int)] = val
            except ValueError:
                result[key] = val
    return result


def main():
    os.makedirs(EXPORTS, exist_ok=True)

    graph = build_evidence_graph()

    json_path = os.path.join(EXPORTS, "openmiir_candidate_evidence_graph.json")
    with open(json_path, "w") as f:
        json.dump(graph, f, indent=2, default=str)

    md_lines = [
        "# OpenMIIR Candidate Evidence Graph",
        f"**Files analyzed**: {graph['files_analyzed']}",
        f"**Total mentions**: {graph['confidence_summary']['total_mentions']}",
        f"**Confirmed**: {graph['confidence_summary']['confirmed']}",
        f"**Strong hypotheses**: {graph['confidence_summary']['strong_hypothesis']}",
        f"**Weak hypotheses**: {graph['confidence_summary']['weak_hypothesis']}",
        "",
        "## README Evidence",
    ]
    for r in graph["readme_evidence"]:
        md_lines.append(f"- [{r['confidence']}] {r['evidence']}")

    md_lines.append("")
    md_lines.append("## Beat File Structure")
    bf = graph["beat_file_structure"]
    md_lines.append(f"- Pattern: `{bf['pattern']}`")
    md_lines.append(f"- Stimuli: {bf['stimuli']}")
    md_lines.append(f"- Cue types: {bf['cue_types']}")
    md_lines.append(f"- Versions: {bf['versions']}")

    md_lines.append("")
    md_lines.append("## Perception/Imagery Status")
    pe = graph["perception_imagery_evidence"]
    md_lines.append(f"- README confirms both conditions: {pe['readme_confirms_both_conditions']}")
    md_lines.append(f"- Explicit code-to-condition map: {not pe['no_explicit_code_to_condition_map']}")
    md_lines.append(f"- Note: {pe['note']}")

    md_path = os.path.join(EXPORTS, "openmiir_candidate_evidence_graph.md")
    with open(md_path, "w") as f:
        f.write("\n".join(md_lines))

    print(f"Candidate miner: files={graph['files_analyzed']} mentions={graph['confidence_summary']['total_mentions']} "
          f"strong={graph['confidence_summary']['strong_hypothesis']}",
          file=sys.stderr)
    print(f"  Perception/imagery confirmed: {graph['perception_imagery_confirmed']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
