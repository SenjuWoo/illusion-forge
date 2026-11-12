"""Honey Select 2 character cards.

The file is a PNG, then product 100, a one-byte length marker 【AIS_Chara】,
version 1.0.0, a language int, two 7-bit GUID strings, then the same lstInfo
table kkloader uses. Coordinate and the other blocks stay as their original
bytes. Custom and Parameter are parsed only when something reads or edits them.
An unmodified save writes the original file bytes back.
"""

from __future__ import annotations

import io
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from kkloader.KoikatuCharaData import BlockData, Custom
from kkloader.funcs import read_lstinfo_blocks, write_lstinfo_blocks

from illusionforge.cards.binary import (
    read_7bit_string,
    read_byte_string,
    read_i32,
    write_7bit_string,
    write_byte_string,
)
from illusionforge.cards.sniff import png_end
from illusionforge.logutil import debug
from illusionforge.spec.sliders import face_name_index


class RawBlock:
    """One lstInfo block kept as the bytes the file already had."""

    def __init__(self, name: str, data: bytes, version: str) -> None:
        self.name = name
        self.data = data
        self.version = version

    def serialize(self) -> tuple[bytes, str, str]:
        return self.data, self.name, self.version


class Hs2Card:
    game = "hs2"

    def __init__(self, original: bytes, path: str | None) -> None:
        self.original = original
        self.path = path
        self.dirty: set[str] = set()
        self._custom: Custom | None = None
        self._parameter: BlockData | None = None
        self._load(original)

    def _load(self, data: bytes) -> None:
        end = png_end(data)
        self.png = data[:end]
        stream = io.BytesIO(data[end:])
        self.product_no = read_i32(stream)
        self.marker = read_byte_string(stream)
        self.version = read_byte_string(stream)
        self.language = read_i32(stream)
        self.user_id = read_7bit_string(stream)
        self.data_id = read_7bit_string(stream)
        raw_payload, entries, self.original_order, self.serialized_order = read_lstinfo_blocks(stream)
        self.trailing = stream.read()
        self.blocks: dict[str, RawBlock] = {}
        self.block_versions: dict[str, str] = {}
        for entry in entries:
            name = str(entry["name"])
            version = str(entry["version"])
            blob = raw_payload[int(entry["pos"]) : int(entry["pos"]) + int(entry["size"])]
            self.blocks[name] = RawBlock(name, blob, version)
            self.block_versions[name] = version
        debug(
            f"hs2 load path={self.path} blocks={list(self.original_order)} "
            f"trailing={len(self.trailing)} language={self.language}"
        )

    @classmethod
    def load(cls, filelike: Path | str | bytes) -> "Hs2Card":
        if isinstance(filelike, bytes):
            return cls(filelike, None)
        path = Path(filelike)
        return cls(path.read_bytes(), str(path))

    def _require(self, name: str) -> RawBlock:
        if name not in self.blocks:
            raise KeyError(f"this Honey Select 2 card has no {name} block")
        return self.blocks[name]

    def face_index_names(self) -> dict[str, int]:
        return face_name_index()

    def _custom_block(self) -> Custom:
        if self._custom is None:
            raw = self._require("Custom")
            self._custom = Custom(data=raw.data, version=raw.version)
        return self._custom

    def _parameter_block(self) -> BlockData:
        if self._parameter is None:
            raw = self._require("Parameter")
            self._parameter = BlockData(name="Parameter", data=raw.data, version=raw.version)
        return self._parameter

    def peek_face(self) -> dict[str, Any]:
        return self._custom_block().data["face"]

    def edit_face(self) -> dict[str, Any]:
        face = self.peek_face()
        self.dirty.add("Custom")
        return face

    def peek_body(self) -> dict[str, Any]:
        return self._custom_block().data["body"]

    def edit_body(self) -> dict[str, Any]:
        body = self.peek_body()
        self.dirty.add("Custom")
        return body

    def peek_hair(self) -> dict[str, Any]:
        return self._custom_block().data["hair"]

    def edit_hair(self) -> dict[str, Any]:
        hair = self.peek_hair()
        self.dirty.add("Custom")
        return hair

    def peek_parameter(self) -> dict[str, Any]:
        data = self._parameter_block().data
        if not isinstance(data, dict):
            raise ValueError("Honey Select 2 Parameter block is not an object")
        return data

    def edit_parameter(self) -> dict[str, Any]:
        data = self.peek_parameter()
        self.dirty.add("Parameter")
        return data

    def _header_bytes(self) -> bytes:
        stream = io.BytesIO()
        stream.write(int(self.product_no).to_bytes(4, "little", signed=True))
        write_byte_string(stream, self.marker)
        write_byte_string(stream, self.version)
        stream.write(int(self.language).to_bytes(4, "little", signed=True))
        write_7bit_string(stream, self.user_id)
        write_7bit_string(stream, self.data_id)
        return stream.getvalue()

    def save_bytes(self) -> bytes:
        if not self.dirty:
            return self.original
        holder = SimpleNamespace()
        for name, raw in self.blocks.items():
            if name == "Custom" and "Custom" in self.dirty and self._custom is not None:
                setattr(holder, name, self._custom)
            elif name == "Parameter" and "Parameter" in self.dirty and self._parameter is not None:
                setattr(holder, name, self._parameter)
            else:
                setattr(holder, name, raw)
        payload = write_lstinfo_blocks(holder, self.serialized_order, self.original_order)
        return self.png + self._header_bytes() + payload + self.trailing

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
        elif isinstance(pupil, dict):
            eye = pupil.get("baseColor")
        hair_color = None
        parts = hair.get("parts")
        if isinstance(parts, list) and parts and isinstance(parts[0], dict):
            hair_color = parts[0].get("baseColor")
        return {
            "game": "hs2",
            "path": self.path,
            "product_no": self.product_no,
            "marker": self.marker.decode("utf-8", errors="replace"),
            "version": self.version.decode("utf-8", errors="replace"),
            "language": self.language,
            "blocks": list(self.original_order),
            "block_versions": dict(self.block_versions),
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
                "skin": body.get("skinColor", body.get("skinMainColor")),
                "hair": hair_color,
                "eye": eye,
                "eyebrow": face.get("eyebrowColor"),
            },
            "clothes": [],
            "clothes_note": "Honey Select 2 outfits stay as raw bytes in this version",
        }
