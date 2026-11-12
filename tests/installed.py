"""Paths to cards in a local game install.

CI and a fresh checkout have no install, so callers skip when the file is absent.
Set ILLUSION_KK_CARD or ILLUSION_HS2_CARD to point a test at one card.
"""

from __future__ import annotations

import os
from pathlib import Path


def installed_card(game: str, *parts: str, env: str = "") -> Path:
    override = os.environ.get(env, "").strip() if env else ""
    if override:
        return Path(override)
    try:
        from illusionforge.discover import discover_games

        info = discover_games().get(game)
    except (OSError, ValueError):
        info = None
    if not info:
        return Path("__missing__") / (parts[-1] if parts else "card.png")
    return Path(info["root"]).joinpath(*parts)
