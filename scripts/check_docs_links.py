"""Fail on broken relative links in project Markdown.

External URLs, anchors, and template placeholders are skipped: this checks that local documentation
actually resolves, not that the network is reachable.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import unquote

LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
ROOT_DOCS = (
    "README.md",
    "AGENTS.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "GOVERNANCE.md",
    "CHANGELOG.md",
    "science/README.md",
)


def markdown_files(root: Path) -> list[Path]:
    files = sorted((root / "docs").rglob("*.md"))
    files += [root / name for name in ROOT_DOCS if (root / name).is_file()]
    return files


def check(root: Path) -> list[str]:
    problems: list[str] = []
    for path in markdown_files(root):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            problems.append(f"{path.relative_to(root)}: cannot read ({exc})")
            continue
        for match in LINK.finditer(text):
            target = match.group(1)
            if target.startswith(("http://", "https://", "mailto:", "#", "tel:")) or "{{" in target:
                continue
            target = unquote(target.split("#", 1)[0])
            if not target:
                continue
            resolved = (path.parent / target).resolve()
            if not resolved.exists():
                line = text.count("\n", 0, match.start()) + 1
                problems.append(f"{path.relative_to(root)}:{line}: missing target {target!r}")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check relative Markdown links.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    root = args.root.resolve()
    problems = check(root)
    if problems:
        print(f"broken Markdown links: {len(problems)}", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        return 1
    print(f"Markdown links OK ({len(markdown_files(root))} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
