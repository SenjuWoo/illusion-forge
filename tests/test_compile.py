"""The prompt table is deterministic and does not invent clothing ids."""

from __future__ import annotations

import unittest

from illusionforge.spec.compile import compile_prompt


class CompileTests(unittest.TestCase):
    def test_hs2_phrase_table(self) -> None:
        spec = compile_prompt(
            'honey select 2 female named "Aoi Tanaka" with a wide face, big eyes, black hair, blue eyes, pale skin, and a dress',
            None,
        )
        self.assertEqual(spec["game"], "hs2")
        self.assertEqual(spec["face_sliders"]["face_width"], 0.75)
        self.assertEqual(spec["face_sliders"]["eye_width_1"], 0.70)
        self.assertEqual(spec["hair_color"], [0.05, 0.05, 0.05, 1.0])
        self.assertEqual(spec["eye_color"], [0.10, 0.20, 0.70, 1.0])
        self.assertEqual(spec["skin_color"], [0.98, 0.90, 0.86, 1.0])
        self.assertEqual(spec["sex"], 1)
        self.assertEqual(spec["name"]["firstname"], "Aoi")
        self.assertEqual(spec["name"]["lastname"], "Tanaka")
        self.assertEqual(spec["name"]["fullname"], "Aoi Tanaka")
        self.assertEqual(spec["clothes"], [])
        self.assertTrue(any(item["text"] == "dress" for item in spec["unmapped"]))
        self.assertFalse(spec["body_sliders"])

    def test_kk_height_and_no_face_names(self) -> None:
        spec = compile_prompt("koikatsu tall woman with a wide face", None)
        self.assertEqual(spec["game"], "kk")
        self.assertEqual(spec["body_sliders"]["height"], 0.85)
        self.assertEqual(spec["sex"], 1)
        self.assertEqual(spec["face_sliders"], {})
        self.assertTrue(any("Koikatsu" in item["reason"] for item in spec["unmapped"]))

    def test_explicit_game_wins(self) -> None:
        spec = compile_prompt("tall", "kk")
        self.assertEqual(spec["game"], "kk")
        self.assertEqual(spec["body_sliders"]["height"], 0.85)

    def test_both_games_is_an_error(self) -> None:
        with self.assertRaises(ValueError):
            compile_prompt("koikatsu and honey select 2", None)

    def test_missing_game_is_an_error(self) -> None:
        with self.assertRaises(ValueError):
            compile_prompt("black hair", None)

    def test_age_ambiguous_word_does_not_set_sex(self) -> None:
        spec = compile_prompt("honey select 2 girl with blue eyes", None)
        self.assertIsNone(spec["sex"])
        self.assertTrue(any("age-ambiguous" in item["text"] for item in spec["unmapped"]))

    def test_short_hair_is_not_height(self) -> None:
        spec = compile_prompt("koikatsu woman with short hair", None)
        self.assertEqual(spec["body_sliders"], {})
        self.assertEqual(spec["sex"], 1)
        very = compile_prompt("koikatsu very short hair", None)
        self.assertEqual(very["body_sliders"], {})
        short = compile_prompt("koikatsu short woman", None)
        self.assertEqual(short["body_sliders"]["height"], 0.25)
        later = compile_prompt("koikatsu woman with short hair who is short", None)
        self.assertEqual(later["body_sliders"]["height"], 0.25)
        punct = compile_prompt("koikatsu woman with short hair,", None)
        self.assertEqual(punct["body_sliders"], {})

    def test_school_uniform_is_one_unmapped_phrase(self) -> None:
        spec = compile_prompt("honey select 2 school uniform", None)
        texts = [item["text"] for item in spec["unmapped"]]
        self.assertIn("school uniform", texts)
        self.assertNotIn("uniform", texts)
        both = compile_prompt("honey select 2 school uniform and a uniform", None)
        both_texts = [item["text"] for item in both["unmapped"]]
        self.assertEqual(both_texts.count("school uniform"), 1)
        self.assertEqual(both_texts.count("uniform"), 1)

    def test_sliders_stay_inside_0_and_1(self) -> None:
        spec = compile_prompt("hs2 small face and slim face and narrow face", None)
        self.assertGreaterEqual(spec["face_sliders"]["face_width"], 0.0)
        self.assertLessEqual(spec["face_sliders"]["face_width"], 1.0)
