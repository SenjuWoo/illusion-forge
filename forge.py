"""Launch the forge without an editable install.

Puts src on the path and calls the CLI. The debug log is unchanged:
ILLUSIONFORGE_DEBUG=1 writes local/logs/illusionforge.log.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from illusionforge.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
