"""Launch the forge without an editable install.

Puts src on the path and calls the CLI. The debug log is unchanged:
ILLUSIONFORGE_DEBUG=1 writes local/logs/illusionforge.log.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))


def _missing_dependency(error: ModuleNotFoundError) -> int:
    """Say which package is missing and how to get it, as the same JSON every
    other failure uses, instead of a traceback from deep inside an import."""
    import json

    print(json.dumps({
        "ok": False,
        "error": "missing_dependency",
        "module": error.name,
        "interpreter": sys.executable,
        "fix": [
            "run forge.cmd, which uses the private environment beside it",
            "or: python -m pip install -r requirements.txt",
        ],
    }, indent=2))
    return 4


if __name__ == "__main__":
    try:
        from illusionforge.cli import main
    except ModuleNotFoundError as error:
        if (error.name or "").split(".")[0] == "illusionforge":
            raise
        raise SystemExit(_missing_dependency(error))
    raise SystemExit(main())
