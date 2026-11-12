"""Library search picks a named card and does not reset its face to 0.5."""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from illusionforge.library.index import load_index, record_from_card, vanilla_label
from illusionforge.library.make import make_from_prompt, spec_on_base
from illusionforge.library.match import rank
from illusionforge.cards.load import load_card

from installed import installed_card

GYARU = installed_card("kk", "UserData", "chara", "female", "Gyaru.png", env="ILLUSION_KK_GYARU")
SISTER = installed_card("kk", "UserData", "chara", "female", "Big Sisterly.png", env="ILLUSION_KK_CARD")


def _card(**kwargs: object) -> dict:
    base = {
        "path": "card.png",
        "game": "kk",
        "sex": 1,
        "personality": None,
        "stem": "",
        "file_tokens": [],
        "name_tokens": [],
        "fullname": "",
        "hair": None,
        "eye": None,
        "skin": None,
        "height": None,
    }
    base.update(kwargs)
    return base


class RankTests(unittest.TestCase):
    def test_filename_beats_personality_and_a_shared_fragment(self) -> None:
        gyaru = _card(path="female/Gyaru.png", stem="gyaru", file_tokens=["gyaru"], personality=13, fullname="Maiko Yamamoto", name_tokens=["maiko", "yamamoto", "mai"])
        other = _card(path="female/Someone.png", stem="someone", file_tokens=["someone"], personality=13, fullname="Someone", name_tokens=["someone"])
        fragment = _card(path="female/Mai.png", stem="mai", file_tokens=["mai"], fullname="Mai", name_tokens=["mai"])
        labels = {"kk": {"13": "Gyaru"}}
        ranked = rank("koikatsu gyaru", [gyaru, other, fragment], labels)
        self.assertEqual(ranked["hits"][0]["path"], "female/Gyaru.png")
        self.assertTrue(ranked["confident"])
        self.assertGreater(ranked["hits"][0]["score"], ranked["hits"][1]["score"])
        fragment_rank = rank("koikatsu maiko", [gyaru, fragment], labels)
        self.assertEqual(fragment_rank["hits"][0]["path"], "female/Gyaru.png")
        self.assertNotEqual(fragment_rank["hits"][0]["reasons"], ["filename"])

    def test_hs2_timestamp_file_matches_the_name_inside(self) -> None:
        tina = _card(path="Modpack/AISChaF_2019.png", game="hs2", stem="aischaf 2019", file_tokens=["aischaf", "2019"], fullname="Tina Armstrong", name_tokens=["tina", "armstrong"])
        gal = _card(path="Community/Gal.png", game="hs2", stem="gal", file_tokens=["gal"], fullname="Gal", name_tokens=["gal"])
        ranked = rank("honey select 2 Tina Armstrong", [tina, gal], {})
        self.assertEqual(ranked["hits"][0]["path"], "Modpack/AISChaF_2019.png")
        self.assertTrue(ranked["confident"])
        alias = rank("honey select 2 gyaru", [tina, gal], {})
        self.assertEqual(alias["hits"][0]["path"], "Community/Gal.png")
        decoy = _card(
            path="Modpack/Vanilla Tina 2.png",
            game="hs2",
            stem="vanilla tina 2",
            file_tokens=["vanilla", "tina", "2"],
            name_tokens=["vanilla", "tina", "2"],
            fullname="Vanilla Tina 2",
        )
        exact = rank("honey select 2 Tina Armstrong", [tina, decoy], {})
        self.assertEqual(exact["hits"][0]["path"], "Modpack/AISChaF_2019.png")

    def test_male_prompt_does_not_return_a_female_card(self) -> None:
        female = _card(path="female/Gyaru.png", stem="gyaru", file_tokens=["gyaru"], sex=1)
        male = _card(path="male/ill_male_01.png", stem="ill male 01", file_tokens=["ill", "male", "01"], sex=0, fullname="柏木")
        ranked = rank("koikatsu male", [female, male], {})
        self.assertTrue(ranked["hits"])
        self.assertTrue(all(hit["sex"] == 0 for hit in ranked["hits"]))
        self.assertFalse(ranked["confident"])

    def test_girl_does_not_filter_sex(self) -> None:
        ranked = rank("koikatsu girl gyaru", [_card(path="female/Gyaru.png", stem="gyaru", file_tokens=["gyaru"], sex=1)], {})
        self.assertIsNone(ranked["sex"])
        self.assertEqual(ranked["hits"][0]["path"], "female/Gyaru.png")

    def test_school_finds_a_schoolgirl_card(self) -> None:
        school = _card(
            path="female/Typical Schoolgirl.png",
            stem="typical schoolgirl",
            file_tokens=["typical", "schoolgirl"],
            personality=21,
        )
        other = _card(path="female/Other.png", stem="other", file_tokens=["other"])
        ranked = rank("koikatsu school uniform", [school, other], {"kk": {"21": ["Typical Schoolgirl"]}})
        self.assertEqual(ranked["hits"][0]["path"], "female/Typical Schoolgirl.png")
        self.assertTrue(ranked["confident"])

    def test_black_hair_picks_the_closer_color_without_claiming_a_name(self) -> None:
        dark = _card(path="dark.png", hair=[0.05, 0.05, 0.05], fullname="Dark")
        blonde = _card(path="blonde.png", hair=[0.86, 0.72, 0.35], fullname="Blonde")
        ranked = rank("koikatsu woman with black hair", [blonde, dark], {})
        self.assertEqual(ranked["hits"][0]["path"], "dark.png")
        self.assertFalse(ranked["confident"])

    def test_stock_male_beats_a_newer_community_card(self) -> None:
        community = _card(path="[Community]/Haruya.png", sex=0, fullname="Haruya Nasuki", name_tokens=["haruya", "nasuki"], mtime=999)
        stock = _card(path="male/ill_male_01.png", sex=0, fullname="柏木", mtime=1)
        ranked = rank("koikatsu male", [community, stock], {})
        self.assertEqual(ranked["hits"][0]["path"], "male/ill_male_01.png")
        self.assertIn("stock card", ranked["hits"][0]["reasons"])
        self.assertFalse(ranked["confident"])
        self.assertTrue(all(hit["sex"] == 0 for hit in ranked["hits"]))

    def test_unknown_name_does_not_fall_back_to_any_card(self) -> None:
        stock = _card(path="male/ill_male_01.png", sex=0, fullname="柏木")
        ranked = rank("koikatsu male xyzzy", [stock], {})
        self.assertEqual(ranked["hits"], [])
        self.assertIn("xyzzy", ranked["query"])

    def test_longer_name_beats_a_shorter_name_and_a_digit_file(self) -> None:
        short = _card(path="a.png", game="hs2", fullname="Tina", name_tokens=["tina"], mtime=50)
        exact = _card(path="b.png", game="hs2", fullname="Tina Armstrong", name_tokens=["tina", "armstrong"], mtime=1)
        digit = _card(path="2.png", game="hs2", stem="2", file_tokens=["2"], fullname="2", name_tokens=["2"], mtime=999)
        ranked = rank("honey select 2 Tina Armstrong", [short, digit, exact], {})
        self.assertEqual(ranked["hits"][0]["path"], "b.png")
        self.assertGreater(ranked["hits"][0]["score"], ranked["hits"][1]["score"])

    def test_newer_copy_wins_a_tied_name(self) -> None:
        older = _card(path="a-early.png", game="hs2", fullname="Tina Armstrong", name_tokens=["tina", "armstrong"], mtime=10)
        newer = _card(path="z-late.png", game="hs2", fullname="Tina Armstrong", name_tokens=["tina", "armstrong"], mtime=20)
        ranked = rank("honey select 2 Tina Armstrong", [older, newer], {})
        self.assertEqual(ranked["hits"][0]["path"], "z-late.png")

    def test_old_folder_loses_to_the_current_card(self) -> None:
        current = _card(path="female/Aria.png", stem="aria", file_tokens=["aria"], fullname="Aria", name_tokens=["aria"], mtime=1)
        old = _card(path="female/Old/Aria.png", stem="aria", file_tokens=["aria"], fullname="Aria", name_tokens=["aria"], mtime=999)
        ranked = rank("koikatsu aria", [old, current], {})
        self.assertEqual(ranked["hits"][0]["path"], "female/Aria.png")
        self.assertIn("older copy", ranked["hits"][1]["reasons"])
        only_old = rank("koikatsu aria", [old], {})
        self.assertEqual(only_old["hits"][0]["path"], "female/Old/Aria.png")

    def test_height_word_is_not_a_character_name(self) -> None:
        named = _card(path="[Community]/Short.png", stem="short", file_tokens=["short"], fullname="Short", name_tokens=["short"], height=0.9)
        stock = _card(path="female/Gyaru.png", stem="gyaru", file_tokens=["gyaru"], height=0.15)
        ranked = rank("koikatsu short woman", [named, stock], {})
        self.assertNotIn("short", ranked["query"])
        self.assertEqual(ranked["hits"][0]["path"], "female/Gyaru.png")
        hair = rank("koikatsu short hair", [named, stock], {})
        self.assertIn("short", hair["query"])
        self.assertEqual(hair["hits"][0]["path"], "[Community]/Short.png")


class SpecOnBaseTests(unittest.TestCase):
    def test_face_phrase_is_a_delta_on_the_card(self) -> None:
        summary = {"game": "hs2", "sex": 1, "face_shape": [0.20, 0.40], "name": {}}
        spec = {
            "game": "hs2",
            "face_sliders": {"face_width": 0.75},
            "body_sliders": {},
            "sex": 1,
            "name": {"firstname": "", "lastname": "", "nickname": "", "fullname": ""},
        }
        adjusted = spec_on_base(spec, summary)
        self.assertAlmostEqual(adjusted["face_sliders"]["0"], 0.45)
        self.assertIsNone(adjusted["sex"])
        self.assertEqual(adjusted["name"], {})


class RealCardTests(unittest.TestCase):
    def test_gyaru_file_is_a_personality_label(self) -> None:
        if not GYARU.is_file():
            self.skipTest("Gyaru card is not installed")
        root = GYARU.parents[1]
        self.assertEqual(vanilla_label(GYARU, root), "Gyaru")
        record = record_from_card(load_card(GYARU), GYARU, root)
        self.assertEqual(record["sex"], 1)
        self.assertEqual(record["stem"], "gyaru")
        self.assertIn("maiko", record["name_tokens"])
        ranked = rank("koikatsu gyaru", [record], {"kk": {str(record["personality"]): "Gyaru"}})
        self.assertTrue(ranked["confident"])
        self.assertEqual(ranked["hits"][0]["path"], str(GYARU.resolve()))

    def test_make_copies_big_sisterly_without_touching_the_source(self) -> None:
        if not SISTER.is_file():
            self.skipTest("Big Sisterly card is not installed")
        before = hashlib.sha256(SISTER.read_bytes()).hexdigest()
        root = SISTER.parents[1]
        record = record_from_card(load_card(SISTER), SISTER, root)
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "out.png"
            report = make_from_prompt(
                "koikatsu big sisterly",
                index={"cards": [record], "personality_labels": {}},
                dest=str(dest),
            )
            self.assertTrue(dest.is_file())
            self.assertTrue(report["match"]["confident"])
            self.assertEqual(dest.read_bytes(), SISTER.read_bytes())
        self.assertEqual(hashlib.sha256(SISTER.read_bytes()).hexdigest(), before)

    def test_make_parses_the_source_once(self) -> None:
        if not SISTER.is_file():
            self.skipTest("Big Sisterly card is not installed")
        root = SISTER.parents[1]
        record = record_from_card(load_card(SISTER), SISTER, root)
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "out.png"
            with patch("illusionforge.cards.apply.load_card", side_effect=AssertionError("parsed twice")):
                report = make_from_prompt(
                    "koikatsu big sisterly",
                    index={"cards": [record], "personality_labels": {}},
                    dest=str(dest),
                )
            self.assertTrue(dest.is_file())
            self.assertTrue(report["match"]["confident"])

    def test_load_index_reuses_the_parsed_catalog(self) -> None:
        first = load_index()
        if not first.get("cards"):
            self.skipTest("card index has not been built")
        second = load_index()
        self.assertIs(first, second)
