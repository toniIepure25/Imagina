#!/usr/bin/env python3
"""Audit public-facing prose for affirmative prohibited claims.

This is a guardrail for README, business, and paper text. It is deliberately narrower than the
frontend claim audit: it checks a fixed set of high-risk phrases and allows explicit negations such
as "does not decode dreams". It does not prove scientific validity and does not replace review.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PROHIBITED = (
    "read your mind",
    "reads your mind",
    "decodes your dreams",
    "decode dreams",
    "shows what you are imagining",
    "cures aphantasia",
    "guarantees lucid dreaming",
    "diagnoses mental health",
    "clinically validated neurofeedback",
    "measures consciousness objectively",
    "mind reading",
    "thought decoding",
    "neural reconstruction",
)

NEGATION = re.compile(
    r"\b(not|no|none|never|neither|nor|cannot|can't|without|does not|do not|is not|isn't|"
    r"aren't|prohibited|forbidden|rejected|unauthorized|not established|not a research goal|"
    r"not allowed|never claim)\b|[✗×]",
    re.IGNORECASE,
)

SCAN_NAMES = ("README.md", "CITATION.cff")
SCAN_DIRS = ("business", "paper")


def markdown_files(root: Path) -> list[Path]:
    files = [root / name for name in SCAN_NAMES if (root / name).is_file()]
    for name in SCAN_DIRS:
        directory = root / name
        if directory.is_dir():
            files.extend(sorted(directory.rglob("*.md")))
    return sorted(set(files))


def audit(files: list[Path], root: Path) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for path in files:
        lines = path.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines):
            lower = line.lower()
            context = " ".join(lines[max(0, index - 1) : index + 2])
            for phrase in PROHIBITED:
                if phrase not in lower:
                    continue
                if NEGATION.search(context):
                    continue
                findings.append(
                    {
                        "file": path.relative_to(root).as_posix(),
                        "line": index + 1,
                        "phrase": phrase,
                        "text": line.strip()[:240],
                    }
                )
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root to audit")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    files = markdown_files(root)
    findings = audit(files, root)
    print(f"[public-claims] {len(files)} files scanned · {len(findings)} affirmative prohibited phrases")
    for finding in findings:
        print(f"  {finding['file']}:{finding['line']}  {finding['phrase']!r}  in {finding['text']!r}", file=sys.stderr)
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
