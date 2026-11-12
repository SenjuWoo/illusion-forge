"""Honey Select 2 face slider names.

The names come from data/hs2_face_sliders.json. That file records the source
and the fact that a local Honey Select 2 card had 59 face floats. Koikatsu
cards measured locally had 52, so these names are not applied to Koikatsu.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


def table_path() -> Path:
    return Path(__file__).resolve().parent.parent / "data" / "hs2_face_sliders.json"


@lru_cache(maxsize=1)
def face_table() -> dict[str, Any]:
    return json.loads(table_path().read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def face_name_index() -> dict[str, int]:
    mapping: dict[str, int] = {}
    for row in face_table()["sliders"]:
        mapping[str(row["en"])] = int(row["index"])
    return mapping


def slider_rows() -> list[dict[str, Any]]:
    return list(face_table()["sliders"])
