"""Identify an Illusion character PNG from the bytes after IEND.

Both games store the card as a PNG plus a product number and a short marker.
Honey Select 2 shares AI Shoujo's marker. This does not decode the face.
"""

from __future__ import annotations

import struct
from pathlib import Path


PNG_SIG = b"\x89PNG\r\n\x1a\n"
MARKERS = {
    "【KoiKatuChara】": "kk",
    "【AIS_Chara】": "hs2",
    "【KoiKatuClothes】": "kk_coordinate",
}


def png_end(data: bytes) -> int:
    if not data.startswith(PNG_SIG):
        raise ValueError("not a PNG")
    idx = 8
    while idx + 8 <= len(data):
        length = struct.unpack_from(">I", data, idx)[0]
        chunk_type = data[idx + 4 : idx + 8]
        idx += 8 + length + 4
        if chunk_type == b"IEND":
            return idx
        if length < 0 or idx > len(data):
            break
    raise ValueError("PNG ended without IEND")


def _read_byte_string(data: bytes, offset: int) -> tuple[bytes, int]:
    if offset >= len(data):
        raise ValueError("truncated header")
    length = data[offset]
    start = offset + 1
    end = start + length
    if end > len(data):
        raise ValueError("truncated marker string")
    return data[start:end], end


def sniff_bytes(data: bytes) -> dict:
    end = png_end(data)
    tail = data[end:]
    if len(tail) < 6:
        return {"kind": "png", "game": None, "marker": None, "png_end": end}
    product = struct.unpack_from("<i", tail, 0)[0]
    try:
        raw, _cursor = _read_byte_string(tail, 4)
        marker = raw.decode("utf-8")
    except (UnicodeDecodeError, ValueError):
        marker = ""
    game = MARKERS.get(marker)
    return {
        "kind": "character" if game in ("kk", "hs2") else ("coordinate" if game else "png"),
        "game": game if game in ("kk", "hs2") else None,
        "file_kind": game,
        "marker": marker or None,
        "product_no": product,
        "png_end": end,
    }


def sniff_path(path: Path | str) -> dict:
    file_path = Path(path)
    info = sniff_bytes(file_path.read_bytes())
    info["path"] = str(file_path)
    return info
