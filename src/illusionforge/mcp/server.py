"""MCP tools for the local forge.

Stdout is reserved for protocol frames. Diagnostics go to the debug log or to
stderr. The server does not launch the game and does not copy the bridge DLL.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from illusionforge import __version__
from illusionforge.bridge.client import exchange
from illusionforge.cards.apply import apply_to_file
from illusionforge.cards.load import load_card
from illusionforge.cards.sniff import sniff_path
from illusionforge.discover import doctor
from illusionforge.library.index import build_index, load_index
from illusionforge.library.make import make_from_prompt
from illusionforge.library.match import rank
from illusionforge.logutil import debug
from illusionforge.paths import forge_root
from illusionforge.spec.compile import compile_prompt
from illusionforge.spec.sliders import face_table, slider_rows

PROTOCOL = "2024-11-05"


def capabilities() -> dict[str, Any]:
    return {
        "forge": "illusionforge",
        "version": __version__,
        "games": ["kk", "hs2"],
        "offline": ["doctor", "sniff", "inspect", "compile", "apply", "sliders", "index", "match", "make"],
        "library": "index reads UserData/chara and make copies the closest card, then applies only the prompt's differences. The outfit on that card is kept.",
        "maker_bridge": ["ping", "status", "apply", "dump_catalog", "screenshot"],
        "face_sliders": {
            "hs2": "named from data/hs2_face_sliders.json (fde_face_v1, 59 names)",
            "kk": "numeric indexes only; a measured card had 52 face floats",
        },
        "body_sliders": {"kk_height": "shapeValueBody[0]", "hs2": "numeric index only, no named height"},
        "not_in_this_version": [
            "Material Editor",
            "ABMX bone sliders",
            "overlay textures",
            "modded clothing ids without a live catalog that includes a slot",
            "a claim that the character looks like the prompt",
        ],
        "visual_checked": False,
    }


def _tool(name: str, description: str, properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "inputSchema": {"type": "object", "properties": properties, "required": required},
    }


def tool_list() -> list[dict[str, Any]]:
    return [
        _tool("illusion_doctor", "Find Koikatsu and Honey Select 2 installs and nearby utility programs.", {}, []),
        _tool("illusion_capabilities", "List what this forge can change and what it leaves alone.", {}, []),
        _tool("illusion_sniff", "Read the marker after the PNG and name the game.", {"path": {"type": "string"}}, ["path"]),
        _tool("illusion_inspect", "Summarize a character card without writing it.", {"path": {"type": "string"}}, ["path"]),
        _tool(
            "illusion_compile",
            "Compile an English prompt into a spec. This does not call a model.",
            {"prompt": {"type": "string"}, "game": {"type": "string"}},
            ["prompt"],
        ),
        _tool(
            "illusion_apply",
            "Write a changed card outside the game folders. A destination inside a game install is refused. The CLI flag --approve-gamedir is not exposed here.",
            {
                "source": {"type": "string"},
                "dest": {"type": "string"},
                "spec": {"type": "object"},
                "prompt": {"type": "string"},
                "game": {"type": "string"},
            },
            ["source"],
        ),
        _tool(
            "illusion_bridge",
            "Send one command to the localhost maker bridge. Fails if the game is not listening.",
            {"op": {"type": "string"}, "payload": {"type": "object"}, "port": {"type": "integer"}},
            ["op"],
        ),
        _tool("illusion_sliders", "Return the Honey Select 2 face slider names and their indexes.", {}, []),
        _tool(
            "illusion_index",
            "Read installed character cards into the local search cache. Does not write into the game.",
            {"game": {"type": "string"}},
            [],
        ),
        _tool(
            "illusion_match",
            "Find the closest installed cards for a prompt. Requires illusion_index first.",
            {"prompt": {"type": "string"}, "game": {"type": "string"}, "limit": {"type": "integer"}},
            ["prompt"],
        ),
        _tool(
            "illusion_make",
            "Copy the closest library card outside the game and apply the prompt. Face phrases move that card's sliders. Its outfit is kept.",
            {"prompt": {"type": "string"}, "game": {"type": "string"}, "dest": {"type": "string"}},
            ["prompt"],
        ),
    ]


def _apply_from_args(args: dict[str, Any]) -> dict[str, Any]:
    source = args.get("source")
    if not source:
        raise ValueError("source is required")
    spec = args.get("spec")
    if spec is None and args.get("prompt"):
        spec = compile_prompt(str(args["prompt"]), args.get("game"))
    if not isinstance(spec, dict):
        raise ValueError("pass spec or prompt")
    dest = args.get("dest")
    if not dest:
        out = forge_root() / "out" / "cards"
        out.mkdir(parents=True, exist_ok=True)
        dest = str(out / (Path(str(source)).stem + ".png"))
    # Game-folder writes stay on the CLI, where the flag is typed by a person.
    return apply_to_file(source, dest, spec, approve_gamedir=False)


def call_tool(name: str, args: dict[str, Any] | None) -> Any:
    args = args or {}
    if name == "illusion_doctor":
        return doctor()
    if name == "illusion_capabilities":
        return capabilities()
    if name == "illusion_sniff":
        return sniff_path(args["path"])
    if name == "illusion_inspect":
        return load_card(args["path"]).summary()
    if name == "illusion_compile":
        return compile_prompt(str(args["prompt"]), args.get("game"))
    if name == "illusion_apply":
        return _apply_from_args(args)
    if name == "illusion_bridge":
        payload = dict(args.get("payload") or {})
        payload["op"] = args["op"]
        return exchange(payload, port=int(args.get("port") or 47331))
    if name == "illusion_sliders":
        table = face_table()
        return {"id": table.get("id"), "source": table.get("source"), "note": table.get("note"), "sliders": slider_rows()}
    if name == "illusion_index":
        return build_index(args.get("game"))
    if name == "illusion_match":
        index = load_index()
        if not index.get("cards"):
            raise ValueError("no card index; run illusion_index")
        ranked = rank(str(args["prompt"]), index["cards"], index.get("personality_labels") or {}, game=args.get("game"), limit=int(args.get("limit") or 8))
        ranked.pop("spec", None)
        return ranked
    if name == "illusion_make":
        return make_from_prompt(str(args["prompt"]), args.get("game"), args.get("dest"))
    raise KeyError(name)


def _result(msg_id: Any, value: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": msg_id, "result": value}


def _error(msg_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}


def handle(message: dict[str, Any]) -> dict[str, Any] | None:
    method = message.get("method")
    msg_id = message.get("id")
    if method == "notifications/initialized":
        return None
    if method == "initialize":
        return _result(msg_id, {
            "protocolVersion": PROTOCOL,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "illusionforge", "version": __version__},
        })
    if method == "ping":
        return _result(msg_id, {})
    if method == "tools/list":
        return _result(msg_id, {"tools": tool_list()})
    if method == "tools/call":
        params = message.get("params") or {}
        name = params.get("name")
        try:
            value = call_tool(str(name), params.get("arguments") or {})
        except KeyError:
            return _error(msg_id, -32602, f"unknown tool {name}")
        except Exception as exc:  # noqa: BLE001 - returned to the client as a tool error
            debug(f"mcp tool {name} failed: {exc}")
            return _result(msg_id, {"content": [{"type": "text", "text": str(exc)}], "isError": True})
        text = json.dumps(value, ensure_ascii=False, default=str)
        return _result(msg_id, {"content": [{"type": "text", "text": text}], "isError": False})
    if msg_id is None:
        return None
    return _error(msg_id, -32601, f"method not found: {method}")


def _read_message(stream: Any) -> dict[str, Any] | None:
    headers: dict[str, str] = {}
    while True:
        line = stream.readline()
        if not line:
            return None
        if line in (b"\r\n", b"\n"):
            break
        decoded = line.decode("ascii", errors="replace")
        if ":" not in decoded:
            continue
        key, value = decoded.split(":", 1)
        headers[key.strip().lower()] = value.strip()
    length = int(headers.get("content-length", "0"))
    if length <= 0 or length > 8 * 1024 * 1024:
        raise ValueError("missing or oversized Content-Length")
    body = stream.read(length)
    if len(body) != length:
        raise ValueError("short MCP body")
    data = json.loads(body.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("MCP body was not an object")
    return data


def _write_message(stream: Any, payload: dict[str, Any]) -> None:
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    stream.write(f"Content-Length: {len(raw)}\r\n\r\n".encode("ascii") + raw)
    stream.flush()


def serve() -> int:
    stdin = sys.stdin.buffer
    stdout = sys.stdout.buffer
    debug("mcp serve")
    while True:
        try:
            message = _read_message(stdin)
        except Exception as exc:  # noqa: BLE001
            _write_message(stdout, _error(None, -32700, str(exc)))
            continue
        if message is None:
            return 0
        try:
            response = handle(message)
        except Exception as exc:  # noqa: BLE001
            response = _error(message.get("id"), -32603, str(exc))
        if response is not None:
            _write_message(stdout, response)
