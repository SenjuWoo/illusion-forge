"""Talk to the maker bridge on 127.0.0.1.

One JSON object per line, both ways. The host is refused unless it is
loopback. A missing listener is a connection error, not a fake success.
"""

from __future__ import annotations

import json
import socket
from typing import Any

from illusionforge.logutil import debug
from illusionforge.spec.sliders import face_name_index

DEFAULT_PORT = 47331
_MAX = 1024 * 1024


def prepare_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Turn Honey Select 2 face names into indexes before the plugin sees them.

    The plugin only accepts numeric slider keys. The name table stays in one
    JSON file on the Python side so the two copies cannot drift.
    """
    if payload.get("op") != "apply":
        return payload
    sliders = payload.get("face_sliders")
    if not isinstance(sliders, dict):
        return payload
    names = face_name_index()
    rewritten: dict[str, Any] = {}
    for key, value in sliders.items():
        text = str(key)
        if text in names:
            rewritten[str(names[text])] = value
        else:
            rewritten[text] = value
    prepared = dict(payload)
    prepared["face_sliders"] = rewritten
    return prepared


def exchange(payload: dict[str, Any], host: str = "127.0.0.1", port: int = DEFAULT_PORT, timeout: float = 8.0) -> dict[str, Any]:
    payload = prepare_payload(payload)
    if host not in ("127.0.0.1", "localhost", "::1"):
        raise ValueError("the maker bridge only accepts a loopback host")
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"
    if len(raw) > _MAX:
        raise ValueError("bridge payload exceeds 1MB")
    debug(f"bridge {host}:{port} op={payload.get('op')}")
    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.settimeout(timeout)
        sock.sendall(raw)
        buf = b""
        while b"\n" not in buf:
            chunk = sock.recv(65536)
            if not chunk:
                break
            buf += chunk
            if len(buf) > _MAX * 2:
                raise ValueError("bridge response exceeds 2MB")
    if not buf:
        raise ConnectionError("the bridge closed without a response")
    line = buf.split(b"\n", 1)[0]
    data = json.loads(line.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("bridge response was not an object")
    return data
