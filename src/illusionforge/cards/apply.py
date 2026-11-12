"""Write a changed card outside the game folders.

The source card is read. The destination is written with a temp file on the
same folder, then replaced. A destination inside a discovered game root is
refused unless approve_gamedir is set. Tests pass an explicit root list.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

from illusionforge.cards.edit import apply_spec
from illusionforge.cards.load import load_card
from illusionforge.discover import discover_games
from illusionforge.logutil import debug


def game_roots(explicit: list[Path] | None = None) -> list[Path]:
    if explicit is not None:
        return [Path(root) for root in explicit]
    return [Path(game["root"]) for game in discover_games().values()]


def under_root(path: Path, roots: list[Path]) -> bool:
    resolved = path.resolve()
    for root in roots:
        base = Path(root).resolve()
        if resolved == base or base in resolved.parents:
            return True
    return False


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    tmp = Path(tmp_name)
    try:
        os.write(fd, data)
        os.fsync(fd)
        os.close(fd)
        fd = -1
        os.replace(tmp, path)
    finally:
        if fd >= 0:
            os.close(fd)
        if tmp.exists():
            tmp.unlink()


def apply_to_file(
    source: Path | str,
    dest: Path | str,
    spec: dict[str, Any],
    *,
    approve_gamedir: bool = False,
    roots: list[Path] | None = None,
    existing: Any | None = None,
) -> dict[str, Any]:
    """Load ``source``, apply ``spec``, and write ``dest``. Returns the edit report.

    ``existing`` is a card already loaded from ``source``. It is reused so a
    caller that inspected the card does not parse the PNG a second time.
    """
    source_path = Path(source)
    dest_path = Path(dest)
    roots = game_roots(roots)
    if source_path.resolve() == dest_path.resolve():
        raise PermissionError("refusing to overwrite the source card; choose a different destination")
    if under_root(dest_path, roots) and not approve_gamedir:
        raise PermissionError(
            "refusing to write inside a game folder without --approve-gamedir; "
            "the default destination is the forge out directory"
        )
    card = None
    if existing is not None:
        existing_path = getattr(existing, "path", None)
        if existing_path and Path(existing_path).resolve() == source_path.resolve():
            card = existing
    if card is None:
        card = load_card(source_path)
    if spec.get("game") and spec["game"] != card.game:
        raise ValueError(f"spec game is {spec['game']} but the card is {card.game}")
    report = apply_spec(card, spec)
    payload = card.save_bytes()
    debug(f"apply dest={dest_path} bytes={len(payload)} approve={approve_gamedir}")
    atomic_write(dest_path, payload)
    report["source"] = str(source_path)
    report["dest"] = str(dest_path)
    report["bytes"] = len(payload)
    report["visual_checked"] = False
    return report
