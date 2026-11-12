"""Round-trips on temp copies of real cards. The installed cards are only read."""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from illusionforge.cards.apply import apply_to_file
from illusionforge.cards.load import load_card
from illusionforge.cards.sniff import sniff_bytes
from installed import installed_card

KK = installed_card("kk", "UserData", "chara", "female", "Big Sisterly.png", env="ILLUSION_KK_CARD")
HS2 = installed_card("hs2", "UserData", "chara", "female", "BR-Chan HS2 Rev2.png", env="ILLUSION_HS2_CARD")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CardTests(unittest.TestCase):
    def test_kk_roundtrip_on_a_copy(self) -> None:
        if not KK.is_file():
            self.skipTest("Koikatsu sample card is not installed")
        before = _sha(KK)
        card = load_card(KK)
        summary = card.summary()
        self.assertEqual(summary["face_slider_count"], 52)
        self.assertEqual(summary["body_slider_count"], 44)
        self.assertEqual(summary["sex"], 1)
        self.assertEqual(summary["name"]["lastname"], "Teranishi")
        self.assertEqual(summary["name"]["firstname"], "Sumire")
        self.assertEqual(card.save_bytes(), KK.read_bytes())
        slot0 = int(summary["clothes"][0]["id"])
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "edited.png"
            report = apply_to_file(
                KK,
                dest,
                {
                    "game": "kk",
                    "name": {"nickname": "ForgeProbe"},
                    "face_sliders": {"0": 0.33},
                    "body_sliders": {"height": 0.81},
                    "hair_color": [0.2, 0.1, 0.05, 1],
                    "clothes": [{"slot": 0, "id": slot0 + 1}],
                },
                roots=[],
            )
            edited = load_card(dest)
            again = edited.summary()
            self.assertEqual(again["name"]["nickname"], "ForgeProbe")
            self.assertEqual(again["name"]["lastname"], "Teranishi")
            self.assertEqual(again["sex"], 1)
            self.assertAlmostEqual(again["face_shape"][0], 0.33, places=5)
            self.assertAlmostEqual(again["body_shape"][0], 0.81, places=5)
            self.assertAlmostEqual(again["colors"]["hair"][0], 0.2, places=5)
            self.assertAlmostEqual(again["colors"]["eyebrow"][0], 0.2, places=5)
            self.assertEqual(again["clothes"][0]["id"], slot0 + 1)
            self.assertEqual(sniff_bytes(dest.read_bytes())["game"], "kk")
            self.assertTrue(any(item["field"] == "name.nickname" for item in report["applied"]))
            self.assertFalse(report["visual_checked"])
        self.assertEqual(_sha(KK), before)

    def test_hs2_identity_and_face_edit(self) -> None:
        if not HS2.is_file():
            self.skipTest("Honey Select 2 sample card is not installed")
        before = _sha(HS2)
        card = load_card(HS2)
        summary = card.summary()
        self.assertEqual(summary["marker"], "【AIS_Chara】")
        self.assertEqual(summary["face_slider_count"], 59)
        self.assertEqual(summary["body_slider_count"], 33)
        self.assertEqual(summary["product_no"], 100)
        self.assertIn("Custom", summary["blocks"])
        self.assertIn("Parameter", summary["blocks"])
        self.assertEqual(card.save_bytes(), HS2.read_bytes())
        sex = summary["sex"]
        fullname = summary["name"]["fullname"]
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "edited.png"
            spec = {
                "game": "hs2",
                "face_sliders": {"face_width": 0.75, "70": 0.1},
                "body_sliders": {"height": 0.9, "0": 0.4},
                "name": {"nickname": "Nope"},
            }
            if fullname:
                spec["name"]["fullname"] = fullname
            if sex is not None:
                spec["sex"] = sex
            report = apply_to_file(HS2, dest, spec, roots=[])
            edited = load_card(dest)
            again = edited.summary()
            self.assertAlmostEqual(again["face_shape"][0], 0.75, places=5)
            self.assertEqual(again["sex"], sex)
            self.assertEqual(again["name"]["fullname"], fullname)
            untouched = Path(tmp) / "noop.png"
            noop = apply_to_file(
                HS2,
                untouched,
                {
                    "game": "hs2",
                    "body_sliders": {"height": 0.9},
                    "name": {"nickname": "Nope"},
                    "face_sliders": {"70": 0.1, "not_a_slider": 0.2},
                },
                roots=[],
            )
            self.assertEqual(untouched.read_bytes(), HS2.read_bytes())
            self.assertTrue(noop["skipped"])
            self.assertEqual(noop["applied"], [])
            self.assertEqual(edited.blocks["Coordinate"].data, card.blocks["Coordinate"].data)
            self.assertEqual(edited.blocks["KKEx"].data, card.blocks["KKEx"].data)
            self.assertEqual(sniff_bytes(dest.read_bytes())["game"], "hs2")
            reasons = " ".join(item["reason"] for item in report["skipped"])
            self.assertIn("Koikatsu", reasons)
            self.assertTrue(any("nickname" in item["field"] for item in report["skipped"]))
            height_skipped = [item for item in report["skipped"] if "height" in item["field"]]
            self.assertTrue(height_skipped)
            self.assertAlmostEqual(again["body_shape"][0], 0.4, places=5)
        self.assertEqual(_sha(HS2), before)

    def test_spec_game_mismatch(self) -> None:
        if not KK.is_file():
            self.skipTest("Koikatsu sample card is not installed")
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "nope.png"
            with self.assertRaises(ValueError):
                apply_to_file(KK, dest, {"game": "hs2", "face_sliders": {}}, roots=[])
            self.assertFalse(dest.exists())
