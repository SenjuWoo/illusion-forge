"""Command line for Illusion Forge.

Card output goes to the path you pass. A path inside a game install is refused
unless --approve-gamedir is present. install-bridge copies the DLL only with
--approve. Debug lines go to local/logs/illusionforge.log when
ILLUSIONFORGE_DEBUG=1.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from illusionforge import __version__
from illusionforge.bridge.client import DEFAULT_PORT, exchange
from illusionforge.cards.apply import apply_to_file
from illusionforge.cards.load import load_card
from illusionforge.cards.sniff import sniff_path
from illusionforge.discover import discover_games, doctor
from illusionforge.mcp.server import capabilities, serve
from illusionforge.paths import forge_root
from illusionforge.library.index import build_index, load_index
from illusionforge.library.make import make_from_prompt
from illusionforge.library.match import rank
from illusionforge.spec.compile import compile_prompt
from illusionforge.spec.sliders import face_table


def _print(data: Any) -> None:
    json.dump(data, sys.stdout, ensure_ascii=False, indent=2, default=str)
    sys.stdout.write("\n")


def _load_spec(args: argparse.Namespace) -> dict[str, Any]:
    if args.spec:
        data = json.loads(Path(args.spec).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("spec file must be an object")
        return data
    if args.prompt:
        return compile_prompt(args.prompt, args.game)
    raise ValueError("pass --spec or --prompt")


def cmd_build_bridge(args: argparse.Namespace) -> int:
    """Compile the maker plugin against each installed game, plus the JSON self-test."""
    root = forge_root()
    project = root / "plugins" / "MakerBridge" / "IllusionForge.MakerBridge.csproj"
    tests = root / "plugins" / "JsonMini.Tests" / "JsonMini.Tests.csproj"
    if not project.is_file():
        print("missing plugins/MakerBridge project", file=sys.stderr)
        return 1
    games = discover_games()
    if args.game:
        games = {key: value for key, value in games.items() if key == args.game}
    built: list[str] = []
    for game_id, info in games.items():
        managed = Path(info["managed"])
        core = Path(info["root"]) / "BepInEx" / "core"
        out = root / "build" / "bridge" / game_id
        if not (core / "BepInEx.dll").is_file():
            print(f"skip {game_id}: BepInEx.dll is not in {core}", file=sys.stderr)
            continue
        command = [
            "dotnet", "build", str(project), "-c", "Release",
            "-o", str(out),
            f"-p:GameManaged={managed}",
            f"-p:BepInExCore={core}",
            "--nologo",
        ]
        print(" ".join(command))
        result = subprocess.run(command, cwd=str(root))
        if result.returncode != 0:
            return result.returncode
        built.append(str(out / "IllusionForge.MakerBridge.dll"))
    result = subprocess.run(
        ["dotnet", "run", "--project", str(tests), "-c", "Release", "--nologo"],
        cwd=str(root),
    )
    if result.returncode != 0:
        return result.returncode
    _print({"built": built, "jsonmini": "ok", "ok": True})
    return 0


def cmd_install_bridge(args: argparse.Namespace) -> int:
    """Copy the built DLL into BepInEx/plugins. Requires --approve."""
    if not args.approve:
        print("refusing to copy into the game without --approve", file=sys.stderr)
        return 2
    games = discover_games()
    info = games.get(args.game)
    if not info:
        print(f"{args.game} was not found", file=sys.stderr)
        return 1
    dll = forge_root() / "build" / "bridge" / args.game / "IllusionForge.MakerBridge.dll"
    if not dll.is_file():
        print("build the bridge first: illusionforge build-bridge", file=sys.stderr)
        return 1
    dest = Path(info["root"]) / "BepInEx" / "plugins" / "IllusionForge" / dll.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(dll, dest)
    _print({"copied": str(dest), "game": args.game})
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="illusionforge", description="Honey Select 2 and Koikatsu character forge")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("doctor", help="find the games and nearby tools").set_defaults(func=lambda _a: (_print(doctor()) or 0))
    sub.add_parser("capabilities", help="what this version will and will not change").set_defaults(
        func=lambda _a: (_print(capabilities()) or 0)
    )

    sniff = sub.add_parser("sniff", help="identify a card from the bytes after IEND")
    sniff.add_argument("path")
    sniff.set_defaults(func=lambda a: (_print(sniff_path(a.path)) or 0))

    inspect = sub.add_parser("inspect", help="summarize a character card")
    inspect.add_argument("path")
    inspect.set_defaults(func=lambda a: (_print(load_card(a.path).summary()) or 0))

    sliders = sub.add_parser("sliders", help="print the Honey Select 2 face slider table")
    sliders.set_defaults(func=lambda _a: (_print(face_table()) or 0))

    index_cmd = sub.add_parser("index", help="read installed character cards into a local search cache")
    index_cmd.add_argument("--game", choices=("kk", "hs2"))
    index_cmd.set_defaults(func=lambda a: (_print(build_index(a.game)) or 0))

    match_cmd = sub.add_parser("match", help="find the closest installed cards for a prompt")
    match_cmd.add_argument("prompt")
    match_cmd.add_argument("--game", choices=("kk", "hs2"))
    match_cmd.add_argument("--limit", type=int, default=8)
    match_cmd.set_defaults(func=_cmd_match)

    make_cmd = sub.add_parser("make", help="copy the closest library card and apply the prompt")
    make_cmd.add_argument("prompt")
    make_cmd.add_argument("--game", choices=("kk", "hs2"))
    make_cmd.add_argument("--dest")
    make_cmd.set_defaults(func=lambda a: (_print(make_from_prompt(a.prompt, a.game, a.dest)) or 0))

    compile_cmd = sub.add_parser("compile", help="turn a prompt into a spec without calling a model")
    compile_cmd.add_argument("prompt")
    compile_cmd.add_argument("--game", choices=("kk", "hs2"))
    compile_cmd.set_defaults(func=lambda a: (_print(compile_prompt(a.prompt, a.game)) or 0))

    apply_cmd = sub.add_parser("apply", help="write a changed card outside the game unless approved")
    apply_cmd.add_argument("--source", required=True)
    apply_cmd.add_argument("--dest", required=True)
    apply_cmd.add_argument("--spec")
    apply_cmd.add_argument("--prompt")
    apply_cmd.add_argument("--game", choices=("kk", "hs2"))
    apply_cmd.add_argument("--approve-gamedir", action="store_true")
    apply_cmd.set_defaults(func=lambda a: (_print(apply_to_file(
        a.source, a.dest, _load_spec(a), approve_gamedir=a.approve_gamedir
    )) or 0))

    bridge = sub.add_parser("bridge", help="send one command to the localhost maker bridge")
    bridge.add_argument("op", choices=("ping", "status", "apply", "dump_catalog", "screenshot"))
    bridge.add_argument("--port", type=int, default=DEFAULT_PORT)
    bridge.add_argument("--payload")
    bridge.set_defaults(func=_cmd_bridge)

    install = sub.add_parser("install-bridge", help="copy the DLL into the game; requires --approve")
    install.add_argument("--game", required=True, choices=("kk", "hs2"))
    install.add_argument("--approve", action="store_true")
    install.set_defaults(func=cmd_install_bridge)

    build = sub.add_parser("build-bridge", help="compile the plugin and run the JSON self-test")
    build.add_argument("--game", choices=("kk", "hs2"))
    build.set_defaults(func=cmd_build_bridge)

    sub.add_parser("mcp", help="speak MCP on stdin/stdout").set_defaults(func=lambda _a: serve())
    return parser


def _cmd_match(args: argparse.Namespace) -> int:
    index = load_index()
    if not index.get("cards"):
        raise ValueError("no card index; run illusionforge index")
    ranked = rank(args.prompt, index["cards"], index.get("personality_labels") or {}, game=args.game, limit=args.limit)
    ranked.pop("spec", None)
    _print(ranked)
    return 0


def _cmd_bridge(args: argparse.Namespace) -> int:
    payload: dict[str, Any] = {"op": args.op}
    if args.payload:
        extra = json.loads(args.payload)
        if not isinstance(extra, dict):
            raise ValueError("payload must be an object")
        extra["op"] = args.op
        payload = extra
    _print(exchange(payload, port=args.port))
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        code = args.func(args)
    except BrokenPipeError:
        return 0
    except Exception as exc:  # noqa: BLE001 - the CLI reports the failure and a non-zero exit
        print(str(exc), file=sys.stderr)
        return 1
    return int(code or 0)


if __name__ == "__main__":
    raise SystemExit(main())
