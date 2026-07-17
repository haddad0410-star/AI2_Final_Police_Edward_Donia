#!/usr/bin/env python3
"""Fail if any src/ Python file exceeds 150 meaningful lines (blank lines and
comment-only lines excluded, per this project's file-length rule)."""

from __future__ import annotations

import sys
from pathlib import Path

LIMIT = 150
SRC = Path(__file__).resolve().parent.parent / "src"


def meaningful_line_count(path: Path) -> int:
    count = 0
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            count += 1
    return count


def main() -> int:
    violations = []
    for path in sorted(SRC.rglob("*.py")):
        n = meaningful_line_count(path)
        if n > LIMIT:
            violations.append((str(path.relative_to(SRC.parent)), n))

    if violations:
        print("FILE LENGTH VIOLATIONS (>150 meaningful lines):")
        for path, n in violations:
            print(f"  {path}: {n} lines")
        return 1

    print(f"OK: all {sum(1 for _ in SRC.rglob('*.py'))} src/ files are <= {LIMIT} meaningful lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
