"""Open a character card once the marker after IEND is known.

Koikatsu and Honey Select 2 do not share a header. A coordinate PNG is
identified and then refused by the editors, because this forge writes characters.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from illusionforge.cards.hs2 import Hs2Card
from illusionforge.cards.kk import KkCard
from illusionforge.cards.sniff import sniff_bytes, sniff_path


def load_card(filelike: Path | str | bytes) -> Any:
    if isinstance(filelike, bytes):
        info = sniff_bytes(filelike)
        data: Path | str | bytes = filelike
    else:
        info = sniff_path(filelike)
        data = filelike
    game = info.get("game")
    if game == "kk":
        return KkCard.load(data)
    if game == "hs2":
        return Hs2Card.load(data)
    kind = info.get("file_kind") or info.get("kind")
    raise ValueError(f"not a Koikatsu or Honey Select 2 character card ({kind})")
