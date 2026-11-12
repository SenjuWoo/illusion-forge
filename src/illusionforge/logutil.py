"""Small debug log. Quiet unless ILLUSIONFORGE_DEBUG=1.

The log lives under the forge's local/logs directory, which is gitignored.
It is for the next failure, not for normal command output.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from illusionforge.paths import forge_root


def debug_enabled() -> bool:
    return os.environ.get("ILLUSIONFORGE_DEBUG", "").strip() not in ("", "0", "false", "False")


def log_path() -> Path:
    path = forge_root() / "local" / "logs" / "illusionforge.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def debug(message: str) -> None:
    if not debug_enabled():
        return
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with log_path().open("a", encoding="utf-8") as handle:
        handle.write(f"{stamp} {message}\n")
