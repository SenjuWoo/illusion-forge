"""Find game installs and the utilities that already sit next to them.

Nothing here copies tools or writes into a game folder. A path is reported
only when the expected executable is actually on disk.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from illusionforge.paths import forge_root

_STEAM_PATH = re.compile(r'"path"\s+"([^"]+)"')

GAMES = {
    "kk": {
        "title": "Koikatsu",
        "exe": "Koikatu.exe",
        "api": ("BepInEx", "plugins", "KKAPI.dll"),
        "managed": ("Koikatu_Data", "Managed"),
        "marker": "【KoiKatuChara】",
    },
    "hs2": {
        "title": "Honey Select 2",
        "exe": "HoneySelect2.exe",
        "api": ("BepInEx", "plugins", "HS2API.dll"),
        "managed": ("HoneySelect2_Data", "Managed"),
        "marker": "【AIS_Chara】",
    },
}

TOOL_GLOBS = (
    ("kkmanager", "KKManager.exe"),
    ("hs2charedit", "HS2CharEdit.exe"),
    ("koikatu_chara_reader", "KoikatuCharaReader.exe"),
    ("sb3utility", "SB3Utility.exe"),
    ("zipstudio", "ZipStudio.exe"),
    ("dnspy", "dnSpy.exe"),
    ("card_image_replacer", "CardImageReplacer.exe"),
)


def local_config() -> dict[str, Any]:
    path = forge_root() / "illusionforge.local.json"
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("illusionforge.local.json must be an object")
    return data


def _configured_roots() -> list[Path]:
    roots: list[Path] = []
    for key in ("ILLUSION_KK_ROOT", "ILLUSION_HS2_ROOT", "ILLUSION_GAME_ROOT"):
        raw = os.environ.get(key, "").strip()
        if raw:
            roots.append(Path(raw))
    config = local_config()
    for key in ("kk", "hs2"):
        raw = config.get(key)
        if isinstance(raw, str) and raw.strip():
            roots.append(Path(raw))
    extra = config.get("extra_roots")
    if isinstance(extra, list):
        roots.extend(Path(item) for item in extra if isinstance(item, str))
    roots.extend(_steam_game_roots())
    return roots


def identify_game(root: Path) -> str | None:
    if not root.is_dir():
        return None
    for game_id, spec in GAMES.items():
        if (root / spec["exe"]).is_file():
            return game_id
    return None


def unescape_vdf(value: str) -> str:
    """Steam writes Windows paths with escaped backslashes."""
    return value.replace("\\\\", "\\")


def library_paths_from_vdf(text: str) -> list[Path]:
    return [Path(unescape_vdf(raw)) for raw in _STEAM_PATH.findall(text)]


def _steam_vdf_files() -> list[Path]:
    files: list[Path] = []
    program_files = os.environ.get("ProgramFiles(x86)", "").strip()
    if program_files:
        files.append(Path(program_files) / "Steam" / "steamapps" / "libraryfolders.vdf")
    home = Path.home()
    files.extend((
        home / ".steam" / "steam" / "steamapps" / "libraryfolders.vdf",
        home / ".local" / "share" / "Steam" / "steamapps" / "libraryfolders.vdf",
        home / "Library" / "Application Support" / "Steam" / "steamapps" / "libraryfolders.vdf",
    ))
    return files


def _steam_game_roots() -> list[Path]:
    """Game folders named by their exe under each Steam library. One directory level."""
    roots: list[Path] = []
    seen: set[str] = set()
    for vdf in _steam_vdf_files():
        if not vdf.is_file():
            continue
        try:
            libraries = library_paths_from_vdf(vdf.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
        for library in libraries:
            common = library / "steamapps" / "common"
            if not common.is_dir():
                continue
            try:
                children = list(common.iterdir())
            except OSError:
                continue
            for child in children:
                if not child.is_dir() or not identify_game(child):
                    continue
                key = str(child.resolve()).casefold()
                if key not in seen:
                    seen.add(key)
                    roots.append(child)
    return roots


def describe_game(game_id: str, root: Path) -> dict[str, Any]:
    spec = GAMES[game_id]
    api = root.joinpath(*spec["api"])
    managed = root.joinpath(*spec["managed"])
    return {
        "id": game_id,
        "title": spec["title"],
        "root": str(root),
        "exe": str(root / spec["exe"]),
        "marker": spec["marker"],
        "api_dll": str(api),
        "api_present": api.is_file(),
        "managed": str(managed),
        "managed_present": managed.is_dir(),
        "bepinex": (root / "BepInEx" / "core" / "BepInEx.dll").is_file(),
        "unityengine": (managed / "UnityEngine.dll").is_file(),
    }


def discover_games() -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    for root in _configured_roots():
        game_id = identify_game(root)
        if game_id and game_id not in found:
            found[game_id] = describe_game(game_id, root)
    return found


# Named utility folders are small. The game root itself is not walked:
# abdata and the managed folders are large and hold no standalone tool exe.
_UTILITY_DIR_NAMES = (
    "[UTILITY] KKManager",
    "[UTILITY] HS2CharEdit",
    "[UTILITY] KoikatuCharaReader",
    "[UTILITY] CardImageReplacer",
    "[UTILITY] Card Image Replacer",
    "[MODDING] Tools",
)


def _remember_tool(hits: list[dict[str, str]], seen: set[str], tool_id: str, match: Path) -> None:
    key = str(match.resolve()).lower()
    if key in seen:
        return
    seen.add(key)
    hits.append({"id": tool_id, "path": str(match)})


def _utility_folders(root: Path) -> list[Path]:
    folders: list[Path] = []
    for name in _UTILITY_DIR_NAMES:
        candidate = root / name
        if candidate.is_dir():
            folders.append(candidate)
    try:
        children = list(root.iterdir())
    except OSError:
        return folders
    for child in children:
        if not child.is_dir():
            continue
        low = child.name.lower()
        if "utility" in low or low in {"tools", "modding", "[modding] tools"}:
            if child not in folders:
                folders.append(child)
    return folders


def _scan_tools(root: Path) -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    if not root.is_dir():
        return hits
    seen: set[str] = set()
    for tool_id, exe_name in TOOL_GLOBS:
        direct = root / exe_name
        if direct.is_file():
            _remember_tool(hits, seen, tool_id, direct)
    for base in _utility_folders(root):
        for tool_id, exe_name in TOOL_GLOBS:
            try:
                matches = list(base.rglob(exe_name))
            except OSError:
                continue
            for match in matches[:1]:
                _remember_tool(hits, seen, tool_id, match)
    return hits


def discover_tools() -> list[dict[str, str]]:
    tools: list[dict[str, str]] = []
    seen: set[str] = set()
    for game in discover_games().values():
        for tool in _scan_tools(Path(game["root"])):
            key = tool["path"].lower()
            if key not in seen:
                seen.add(key)
                tool = dict(tool)
                tool["game"] = game["id"]
                tools.append(tool)
    return tools


def doctor() -> dict[str, Any]:
    games = discover_games()
    return {
        "ok": True,
        "forge": "illusionforge",
        "games": games,
        "missing_games": [game_id for game_id in GAMES if game_id not in games],
        "tools": discover_tools(),
        "bridge_port_default": 47331,
        "notes": [
            "Card writes stay outside the game folder unless apply is given an explicit destination and --approve-gamedir.",
            "The maker bridge is a separate DLL. doctor does not launch the game and does not copy that DLL in.",
        ],
    }
