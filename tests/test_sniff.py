"""Marker detection on a one-pixel PNG plus a fake card tail. No game files."""

from __future__ import annotations

import struct
import unittest
import zlib

from illusionforge.cards.sniff import sniff_bytes


def _chunk(tag: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(tag + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)


def _png() -> bytes:
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) + _chunk(b"IEND", b"")


def _tail(marker: str) -> bytes:
    raw = marker.encode("utf-8")
    return struct.pack("<i", 100) + bytes((len(raw),)) + raw + bytes((5,)) + b"0.0.0"


class SniffTests(unittest.TestCase):
    def test_kk_marker(self) -> None:
        info = sniff_bytes(_png() + _tail("【KoiKatuChara】"))
        self.assertEqual(info["game"], "kk")
        self.assertEqual(info["kind"], "character")
        self.assertEqual(info["product_no"], 100)

    def test_hs2_marker(self) -> None:
        info = sniff_bytes(_png() + _tail("【AIS_Chara】"))
        self.assertEqual(info["game"], "hs2")
        self.assertEqual(info["marker"], "【AIS_Chara】")

    def test_plain_png(self) -> None:
        info = sniff_bytes(_png())
        self.assertEqual(info["kind"], "png")
        self.assertIsNone(info["game"])

    def test_rejects_non_png(self) -> None:
        with self.assertRaises(ValueError):
            sniff_bytes(b"not a png")
