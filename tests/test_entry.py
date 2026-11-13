"""The entry script and the batch launchers, started as a user starts them."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class EntryTests(unittest.TestCase):
    def test_missing_dependency_is_one_json_error_not_a_traceback(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            (home / "forge.py").write_bytes((ROOT / "forge.py").read_bytes())
            package = home / "src" / "illusionforge"
            package.mkdir(parents=True)
            (package / "__init__.py").write_text("", encoding="utf-8")
            (package / "cli.py").write_text("import a_card_library_that_is_not_installed\n", encoding="utf-8")
            env = {key: value for key, value in os.environ.items() if key.upper() != "PYTHONPATH"}
            done = subprocess.run([sys.executable, str(home / "forge.py"), "doctor"], capture_output=True, text=True,
                                  encoding="utf-8", env=env, timeout=60)
        self.assertEqual(done.returncode, 4, done.stdout + done.stderr)
        self.assertNotIn("Traceback", done.stderr)
        report = json.loads(done.stdout)
        self.assertEqual(report["error"], "missing_dependency")
        self.assertEqual(report["module"], "a_card_library_that_is_not_installed")
        self.assertTrue(any("forge.cmd" in line for line in report["fix"]))

    def test_a_broken_package_is_still_a_real_error(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            (home / "forge.py").write_bytes((ROOT / "forge.py").read_bytes())
            (home / "src").mkdir()
            done = subprocess.run([sys.executable, str(home / "forge.py")], capture_output=True, text=True,
                                  encoding="utf-8", timeout=60)
        self.assertNotEqual(done.returncode, 4)
        self.assertIn("illusionforge", done.stderr)

    def test_batch_launchers_pin_delayed_expansion_off(self):
        for name in ("forge.cmd", "START-HERE.bat", "Run-Tests.bat"):
            head = (ROOT / name).read_bytes().splitlines()[:4]
            self.assertTrue(any(b"disabledelayedexpansion" in line.lower() for line in head), name)


if __name__ == "__main__":
    unittest.main()
