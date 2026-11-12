"""Locate the forge root from this file, not from the current directory.

The root is the directory that contains pyproject.toml. Tests and the CLI
both call this so a launch from another folder still finds data files.
"""

from __future__ import annotations

from pathlib import Path


def forge_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").is_file() and (parent / "src" / "illusionforge").is_dir():
            return parent
    return here.parents[2]
