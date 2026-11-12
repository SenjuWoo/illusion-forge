"""Tool discovery stays inside utility folders. A deep abdata decoy is ignored."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from illusionforge.discover import _STEAM_PATH, _scan_tools, unescape_vdf


class DiscoverTests(unittest.TestCase):
    def test_skips_deep_decoy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decoy = root / "abdata" / "deep" / "nested"
            decoy.mkdir(parents=True)
            (decoy / "KKManager.exe").write_bytes(b"nope")
            utility = root / "[UTILITY] KKManager"
            utility.mkdir()
            (utility / "KKManager.exe").write_bytes(b"tool")
            hits = _scan_tools(root)
        paths = [hit["path"] for hit in hits]
        self.assertEqual(len(paths), 1)
        self.assertIn("[UTILITY] KKManager", paths[0])

    def test_steam_library_path_unescapes_backslashes(self) -> None:
        sample = '"path"\t\t"D:\\\\SteamLibrary"'
        found = _STEAM_PATH.findall(sample)
        self.assertEqual(found, ["D:\\\\SteamLibrary"])
        self.assertEqual(unescape_vdf(found[0]), "D:\\SteamLibrary")
