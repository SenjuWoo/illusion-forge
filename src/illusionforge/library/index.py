"""Build a searchable cache of the character cards under UserData/chara.

Each PNG is read once. A card that fails to parse is counted and skipped.
The cache is local/indexes/cards.json. Re-running reuses a card whose size
and modification time did not change.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from illusionforge.cards.hs2 import Hs2Card
from illusionforge.cards.kk import KkCard
from illusionforge.cards.sniff import sniff_bytes
from illusionforge.discover import discover_games, local_config
from illusionforge.logutil import debug
from illusionforge.paths import forge_root

INDEX_VERSION = 1
_TOKEN = re.compile(r"[^\W_]+", re.UNICODE)
# One process, one parsed catalog. The key is the cache file's size and mtime.
# Callers must not mutate the returned card dicts.
_CACHE: dict[str, Any] | None = None
_CACHE_KEY: tuple[int, int] | None = None


def index_path() -> Path:
    """Cache file. It is under local/, which is not part of the source tree."""
    return forge_root() / "local" / "indexes" / "cards.json"


def load_index() -> dict[str, Any]:
    """Return the cache, or an empty catalog when it has not been built."""
    global _CACHE, _CACHE_KEY
    path = index_path()
    if not path.is_file():
        _CACHE = None
        _CACHE_KEY = None
        return {"version": INDEX_VERSION, "cards": [], "personality_labels": {}}
    stat = path.stat()
    key = (stat.st_mtime_ns, stat.st_size)
    if _CACHE is not None and _CACHE_KEY == key:
        return _CACHE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": INDEX_VERSION, "cards": [], "personality_labels": {}}
    if not isinstance(data, dict) or data.get("version") != INDEX_VERSION:
        return {"version": INDEX_VERSION, "cards": [], "personality_labels": {}}
    data.setdefault("cards", [])
    data.setdefault("personality_labels", {})
    _CACHE = data
    _CACHE_KEY = key
    return data


def card_folders(game: str | None = None) -> list[tuple[str | None, Path]]:
    """Game character folders, plus any extra card_roots in the local config."""
    folders: list[tuple[str | None, Path]] = []
    for game_id, info in discover_games().items():
        if game and game_id != game:
            continue
        chara = Path(info["root"]) / "UserData" / "chara"
        if chara.is_dir():
            folders.append((game_id, chara))
    if game:
        return folders
    extra = local_config().get("card_roots") or []
    if isinstance(extra, list):
        for item in extra:
            if isinstance(item, str) and item.strip():
                path = Path(item)
                if path.is_dir():
                    folders.append((None, path))
    return folders


def tokens(text: str) -> list[str]:
    """Split a filename or a character name into lowercase words."""
    return [part.casefold() for part in _TOKEN.findall(text or "")]


def _rgb(value: Any) -> list[float] | None:
    if not isinstance(value, list) or len(value) < 3:
        return None
    try:
        return [round(float(value[0]), 3), round(float(value[1]), 3), round(float(value[2]), 3)]
    except (TypeError, ValueError):
        return None


def _hair_color(hair: dict[str, Any]) -> Any:
    parts = hair.get("parts")
    if isinstance(parts, list) and parts and isinstance(parts[0], dict):
        return parts[0].get("baseColor")
    return None


def _eye_color(face: dict[str, Any]) -> Any:
    pupil = face.get("pupil")
    if isinstance(pupil, list) and pupil and isinstance(pupil[0], dict):
        return pupil[0].get("baseColor")
    if isinstance(pupil, dict):
        return pupil.get("baseColor")
    return None


def vanilla_label(path: Path, chara_root: Path) -> str | None:
    """Personality name for a stock card that sits directly in female or male.

    "Gyaru 2" counts as Gyaru. Timestamp names and codes with digits do not,
    because those are not personality labels.
    """
    if path.parent.parent != chara_root:
        return None
    if path.parent.name.casefold() not in {"female", "male"}:
        return None
    stem = re.sub(r"\s+\d+$", "", path.stem).strip()
    if not stem or re.search(r"\d", stem):
        return None
    return stem


def record_from_card(card: Any, path: Path, chara_root: Path) -> dict[str, Any]:
    """Pull the fields the matcher needs. The face array is not stored."""
    param = card.peek_parameter()
    face = card.peek_face()
    body = card.peek_body()
    hair = card.peek_hair()
    name_parts: list[str] = []
    for key in ("firstname", "lastname", "nickname", "fullname"):
        value = param.get(key)
        if isinstance(value, str) and value.strip():
            name_parts.append(value.strip())
    full = param.get("fullname")
    if not isinstance(full, str) or not full.strip():
        first = param.get("firstname") if isinstance(param.get("firstname"), str) else ""
        last = param.get("lastname") if isinstance(param.get("lastname"), str) else ""
        full = " ".join(part for part in (first.strip(), last.strip()) if part)
    shape = body.get("shapeValueBody") if isinstance(body, dict) else None
    height = None
    if card.game == "kk" and isinstance(shape, list) and shape:
        try:
            height = round(float(shape[0]), 4)
        except (TypeError, ValueError):
            height = None
    skin = None
    if isinstance(body, dict):
        skin = body.get("skinMainColor", body.get("skinColor"))
    stat = path.stat()
    sex = param.get("sex")
    personality = param.get("personality")
    return {
        "path": str(path.resolve()),
        "game": card.game,
        "sex": int(sex) if isinstance(sex, int) else None,
        "personality": int(personality) if isinstance(personality, int) else None,
        "stem": " ".join(tokens(path.stem)),
        "file_tokens": tokens(path.stem),
        "name_tokens": tokens(" ".join(name_parts)),
        "fullname": full.strip() if isinstance(full, str) else "",
        "hair": _rgb(_hair_color(hair if isinstance(hair, dict) else {})),
        "eye": _rgb(_eye_color(face if isinstance(face, dict) else {})),
        "skin": _rgb(skin),
        "height": height,
        "vanilla_label": vanilla_label(path, chara_root),
        "size": stat.st_size,
        "mtime": int(stat.st_mtime),
    }


def _labels(records: list[dict[str, Any]]) -> dict[str, dict[str, list[str]]]:
    """Map a personality id to every stock filename that uses it.

    Koikatsu ships both Gyaru.png and ギャル.png for the same id. Keeping one
    would make the other language unsearchable.
    """
    found: dict[tuple[str, str], list[str]] = {}
    for record in records:
        label = record.get("vanilla_label")
        personality = record.get("personality")
        if not label or personality is None:
            continue
        key = (str(record["game"]), str(personality))
        bucket = found.setdefault(key, [])
        if str(label) not in bucket:
            bucket.append(str(label))
    labels: dict[str, dict[str, list[str]]] = {}
    for (game, personality), names in found.items():
        labels.setdefault(game, {})[personality] = sorted(names, key=len)
    return labels


def _load_png(path: Path) -> Any | None:
    """Return a card, or None when the PNG is not a character card."""
    data = path.read_bytes()
    info = sniff_bytes(data)
    game = info.get("game")
    if game == "kk":
        return KkCard.load(data)
    if game == "hs2":
        return Hs2Card.load(data)
    return None


def build_index(game: str | None = None) -> dict[str, Any]:
    """Read the character folders and write the cache. Game files stay untouched."""
    previous = load_index()
    reusable = {str(item.get("path")): item for item in previous.get("cards") or [] if isinstance(item, dict)}
    records: list[dict[str, Any]] = []
    if game:
        records.extend(item for item in reusable.values() if item.get("game") != game)
    seen = {str(item.get("path")) for item in records}
    failed = 0
    skipped = 0
    reused = 0
    parsed = 0
    scanned = 0
    for _hint, folder in card_folders(game):
        for path in folder.rglob("*.png"):
            if not path.is_file():
                continue
            scanned += 1
            resolved = str(path.resolve())
            if resolved in seen:
                continue
            seen.add(resolved)
            stat = path.stat()
            old = reusable.get(resolved)
            if (
                isinstance(old, dict)
                and old.get("size") == stat.st_size
                and old.get("mtime") == int(stat.st_mtime)
                and (not game or old.get("game") == game)
            ):
                records.append(old)
                reused += 1
            else:
                try:
                    card = _load_png(path)
                except Exception as exc:  # noqa: BLE001 - one bad card does not stop the index
                    failed += 1
                    debug(f"index skip {path}: {type(exc).__name__}: {exc}")
                    continue
                if card is None:
                    skipped += 1
                    continue
                try:
                    records.append(record_from_card(card, path, folder))
                except Exception as exc:  # noqa: BLE001 - keep indexing the rest of the folder
                    failed += 1
                    debug(f"index record {path}: {type(exc).__name__}: {exc}")
                    continue
                parsed += 1
            if scanned % 200 == 0:
                print(f"indexed {scanned} files", file=sys.stderr)
    labels = _labels(records)
    counts: dict[str, dict[str, int]] = {}
    for record in records:
        bucket = counts.setdefault(str(record.get("game")), {})
        sex_key = str(record.get("sex"))
        bucket[sex_key] = bucket.get(sex_key, 0) + 1
    stored = records
    payload = {
        "version": INDEX_VERSION,
        "cards": stored,
        "personality_labels": labels,
        "counts": counts,
        "failed": failed,
        "skipped": skipped,
    }
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    from illusionforge.cards.apply import atomic_write

    atomic_write(index_path(), raw)
    debug(f"index cards={len(stored)} parsed={parsed} reused={reused} failed={failed} skipped={skipped}")
    return {
        "ok": True,
        "path": str(index_path()),
        "cards": len(stored),
        "parsed": parsed,
        "reused": reused,
        "failed": failed,
        "skipped": skipped,
        "counts": counts,
        "personality_labels": labels,
    }
