"""Koikatsu character cards through kkloader.

An unmodified save returns the original file bytes. An edit is reserialized
by kkloader, which rebuilds every block, so a changed file is checked by
reading the values back rather than by comparing bytes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from kkloader import KoikatuCharaData

from illusionforge.logutil import debug


class KkCard:
    game = "kk"

    def __init__(self, kc: KoikatuCharaData, original: bytes, path: str | None) -> None:
        self.kc = kc
        self.original = original
        self.path = path
        self.dirty: set[str] = set()

    @classmethod
    def load(cls, filelike: Path | str | bytes) -> "KkCard":
        if isinstance(filelike, bytes):
            original = filelike
            path = None
        else:
            path = str(filelike)
            original = Path(filelike).read_bytes()
        kc = KoikatuCharaData.load(original)
        debug(f"kk load path={path} blocks={getattr(kc, 'blockdata', [])}")
        return cls(kc, original, path)

    def face_index_names(self) -> dict[str, int]:
        return {}

    def peek_face(self) -> dict[str, Any]:
        return self.kc["Custom"].data["face"]

    def edit_face(self) -> dict[str, Any]:
        self.dirty.add("Custom")
        return self.peek_face()

    def peek_body(self) -> dict[str, Any]:
        return self.kc["Custom"].data["body"]

    def edit_body(self) -> dict[str, Any]:
        self.dirty.add("Custom")
        return self.peek_body()

    def peek_hair(self) -> dict[str, Any]:
        return self.kc["Custom"].data["hair"]

    def edit_hair(self) -> dict[str, Any]:
        self.dirty.add("Custom")
        return self.peek_hair()

    def peek_parameter(self) -> dict[str, Any]:
        return self.kc["Parameter"].data

    def edit_parameter(self) -> dict[str, Any]:
        self.dirty.add("Parameter")
        return self.peek_parameter()

    def set_kk_clothes_id(self, slot: int, cloth_id: int) -> None:
        """Set one clothing part id. The slot must already exist on outfit 0."""
        coordinate = self.kc["Coordinate"].data
        if not isinstance(coordinate, list) or not coordinate:
            raise ValueError("this Koikatsu card has no outfit list")
        clothes = coordinate[0]["clothes"]
        parts = clothes["parts"]
        if slot < 0 or slot >= len(parts):
            raise IndexError(f"clothes slot {slot} is outside 0..{len(parts) - 1}")
        if "id" not in parts[slot]:
            raise KeyError("clothes part has no id")
        parts[slot]["id"] = int(cloth_id)
        self.dirty.add("Coordinate")

    def save_bytes(self) -> bytes:
        if not self.dirty:
            return self.original
        return bytes(self.kc)

    def summary(self) -> dict[str, Any]:
        face = self.peek_face()
        body = self.peek_body()
        hair = self.peek_hair()
        param = self.peek_parameter()
        shape_face = face.get("shapeValueFace") or []
        shape_body = body.get("shapeValueBody") or []
        pupil = face.get("pupil")
        eye = None
        if isinstance(pupil, list) and pupil and isinstance(pupil[0], dict):
            eye = pupil[0].get("baseColor")
        hair_color = None
        parts = hair.get("parts")
        if isinstance(parts, list) and parts and isinstance(parts[0], dict):
            hair_color = parts[0].get("baseColor")
        clothes: list[dict[str, Any]] = []
        coordinate = getattr(self.kc["Coordinate"], "data", None)
        if isinstance(coordinate, list) and coordinate:
            parts = coordinate[0].get("clothes", {}).get("parts", [])
            for index, part in enumerate(parts):
                if isinstance(part, dict):
                    clothes.append({"slot": index, "id": part.get("id")})
        return {
            "game": "kk",
            "path": self.path,
            "product_no": self.kc.product_no,
            "marker": self.kc.header.decode("utf-8", errors="replace"),
            "version": self.kc.version.decode("utf-8", errors="replace"),
            "blocks": list(self.kc.blockdata),
            "name": {
                "lastname": param.get("lastname"),
                "firstname": param.get("firstname"),
                "nickname": param.get("nickname"),
                "fullname": param.get("fullname"),
            },
            "sex": param.get("sex"),
            "personality": param.get("personality"),
            "face_slider_count": len(shape_face),
            "body_slider_count": len(shape_body),
            "face_shape": list(shape_face),
            "body_shape": list(shape_body),
            "colors": {
                "skin": body.get("skinMainColor", body.get("skinColor")),
                "hair": hair_color,
                "eye": eye,
                "eyebrow": face.get("eyebrowColor"),
            },
            "clothes": clothes,
        }
