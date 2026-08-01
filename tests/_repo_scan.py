"""Shared test helper: list real project files to scan for secret/credential
checks, falling back to a full filesystem walk when ``.git`` is absent (e.g.
inside an extracted LOCAL_REVIEW ZIP, which deliberately excludes ``.git``)
-- these security scans must never silently skip just because there is no
git history to ask.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

#: Directories that are never real project content, whichever listing mode
#: is used -- matches what a committed ``.gitignore`` already excludes.
_ALWAYS_EXCLUDED_DIRS = frozenset(
    {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", "htmlcov"}
)


def repo_files(repo_root: Path) -> list[str]:
    """Repo-relative POSIX paths of every real project file: git-tracked
    files when ``.git`` exists (identical to the real committed history), or
    every on-disk file outside the always-excluded dirs when it doesn't."""
    if (repo_root / ".git").exists():
        out = subprocess.run(
            ["git", "ls-files"], cwd=repo_root, capture_output=True, text=True, check=True
        ).stdout
        return [line for line in out.splitlines() if line]
    files: list[str] = []
    for path in repo_root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(repo_root)
        if any(part in _ALWAYS_EXCLUDED_DIRS for part in rel.parts):
            continue
        files.append(rel.as_posix())
    return files
