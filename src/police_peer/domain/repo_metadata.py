"""Accurate, actually-computed repository metadata for the declaration.

The git commit hash is obtained by really running ``git rev-parse HEAD`` against
THIS repo when a ``.git`` directory is present -- never assumed. A clean-extracted
review ZIP deliberately excludes ``.git``; for that case a ``BUILD_COMMIT`` file
(written into the ZIP at packaging time from the real HEAD at build time) is
read instead, so provenance is never silently lost, never fabricated. The code
version is read from ``pyproject.toml``.
"""

from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path


def git_commit_hash(repo_root: Path) -> str:
    """The exact commit this code was built from: a real ``git rev-parse
    HEAD`` when ``.git`` exists, else the packaged ``BUILD_COMMIT`` file."""
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
        return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        build_commit = repo_root / "BUILD_COMMIT"
        if build_commit.exists():
            return build_commit.read_text(encoding="utf-8").strip()
        return "unavailable: no .git and no BUILD_COMMIT file"


def code_version(pyproject_path: Path) -> str:
    """The ``[project].version`` string read from ``pyproject.toml``."""
    try:
        data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
        return str(data["project"]["version"])
    except (OSError, KeyError, tomllib.TOMLDecodeError):  # pragma: no cover - defensive
        return "unavailable: pyproject.toml version not found"
