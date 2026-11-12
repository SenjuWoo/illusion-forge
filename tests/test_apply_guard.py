"""Destinations inside a game root are refused unless the flag is explicit."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from illusionforge.cards.apply import apply_to_file, under_root

from installed import installed_card

KK = installed_card("kk", "UserData", "chara", "female", "Big Sisterly.png", env="ILLUSION_KK_CARD")


class GuardTests(unittest.TestCase):
    def test_under_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inside = root / "UserData" / "chara" / "card.png"
            outside = root.parent / "elsewhere.png"
            self.assertTrue(under_root(inside, [root]))
            self.assertFalse(under_root(outside, [root]))

    def test_apply_refuses_game_destination(self) -> None:
        if not KK.is_file():
            self.skipTest("Koikatsu sample card is not installed")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "game"
            dest = root / "UserData" / "chara" / "card.png"
            before = KK.read_bytes()
            with self.assertRaises(PermissionError):
                apply_to_file(KK, dest, {"name": {"nickname": "ShouldNotWrite"}}, roots=[root])
            self.assertFalse(dest.exists())
            self.assertEqual(KK.read_bytes(), before)
