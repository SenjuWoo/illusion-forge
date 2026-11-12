"""Copy the closest library card and apply only the prompt's differences.

Face phrases move that card's existing sliders. They do not reset the face
to the middle of the slider. The card's outfit is kept. The write goes to
the destination, which the apply guard refuses when it is inside a game.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from illusionforge.cards.apply import apply_to_file
from illusionforge.cards.load import load_card
from illusionforge.library.index import load_index
from illusionforge.library.match import rank
from illusionforge.logutil import debug
from illusionforge.paths import forge_root
from illusionforge.spec.sliders import face_name_index


def spec_on_base(spec: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
    """Rewrite absolute phrase-table face values into deltas on this card."""
    adjusted = dict(spec)
    shape = summary.get("face_shape") or []
    names = face_name_index() if summary.get("game") == "hs2" else {}
    face: dict[str, float] = {}
    for key, raw in (spec.get("face_sliders") or {}).items():
        if str(key) in names:
            index = names[str(key)]
        elif isinstance(key, int) or (isinstance(key, str) and str(key).lstrip("-").isdigit()):
            index = int(key)
        else:
            continue
        if index < 0 or index >= len(shape):
            continue
        delta = float(raw) - 0.5
        face[str(index)] = max(0.0, min(1.0, float(shape[index]) + delta))
    adjusted["face_sliders"] = face
    if spec.get("sex") is not None and spec.get("sex") == summary.get("sex"):
        adjusted["sex"] = None
    name = spec.get("name") or {}
    if not isinstance(name, dict) or not any(name.values()):
        adjusted["name"] = {}
    return adjusted


def _dest_for(source: Path, game: str, dest: str | None) -> Path:
    if dest:
        return Path(dest)
    slug = re.sub(r"[^\w\-]+", "-", source.stem, flags=re.UNICODE).strip("-")[:48] or "card"
    return forge_root() / "out" / "cards" / f"{game}-{slug}.png"


def make_from_prompt(
    prompt: str,
    game: str | None = None,
    dest: str | None = None,
    limit: int = 8,
    index: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Write a card outside the game from the closest indexed character."""
    index = load_index() if index is None else index
    cards = index.get("cards") or []
    if not cards:
        raise ValueError("no card index; run illusionforge index")
    ranked = rank(prompt, cards, index.get("personality_labels") or {}, game=game, limit=limit)
    hits = ranked["hits"]
    if not hits:
        raise ValueError(f"no library card matched; searched {ranked['searched']} {ranked['game']} cards")
    best = hits[0]
    source = Path(str(best["path"]))
    card = load_card(source)
    summary = card.summary()
    spec = spec_on_base(ranked["spec"], summary)
    target = _dest_for(source, str(summary.get("game") or ranked["game"]), dest)
    report = apply_to_file(source, target, spec, existing=card)
    report["source"] = str(source)
    report["dest"] = str(target)
    report["match"] = {
        "score": best["score"],
        "reasons": best["reasons"],
        "confident": ranked["confident"],
        "fullname": best.get("fullname") or "",
        "searched": ranked["searched"],
    }
    report["alternatives"] = [
        {"path": hit["path"], "score": hit["score"], "fullname": hit.get("fullname") or "", "reasons": hit["reasons"]}
        for hit in hits[1:4]
    ]
    notes = list(report.get("notes") or [])
    notes.append("The base is a library card. Face phrases are added to that card's sliders. Its outfit is kept.")
    notes.append("Clothing words are not turned into item ids.")
    if not ranked["confident"]:
        notes.append("No character name or type matched. The card is the nearest sex, color, or height hit.")
    report["notes"] = notes
    report["visual_checked"] = False
    debug(f"make source={source} dest={target} confident={ranked['confident']} score={best['score']}")
    return report
