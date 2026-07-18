"""Accurate, actually-computed repository metadata for the declaration.

The git commit hash is obtained by really running ``git rev-parse HEAD`` against
THIS repo -- never assumed. The code version is read from ``pyproject.toml``.
Both fail loudly-but-safely to a marker string rather than a fabricated value.
"""

from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path


def git_commit_hash(repo_root: Path) -> str:
    """The exact ``HEAD`` commit of ``repo_root`` via a real subprocess call."""
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
        return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):  # pragma: no cover - git always present here
        return "unavailable: git rev-parse failed"


def code_version(pyproject_path: Path) -> str:
    """The ``[project].version`` string read from ``pyproject.toml``."""
    try:
        data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
        return str(data["project"]["version"])
    except (OSError, KeyError, tomllib.TOMLDecodeError):  # pragma: no cover - defensive
        return "unavailable: pyproject.toml version not found"
