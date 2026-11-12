"""Stdio MCP initialize and tools/list. No game launch."""

from __future__ import annotations

import json
import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"


def _frame(payload: dict) -> bytes:
    raw = json.dumps(payload).encode("utf-8")
    return f"Content-Length: {len(raw)}\r\n\r\n".encode("ascii") + raw


def _read(stream) -> dict:
    headers = {}
    while True:
        line = stream.readline()
        if line in (b"\r\n", b"\n"):
            break
        key, value = line.decode("ascii").split(":", 1)
        headers[key.strip().lower()] = value.strip()
    length = int(headers["content-length"])
    return json.loads(stream.read(length).decode("utf-8"))


class McpTests(unittest.TestCase):
    def test_initialize_and_list(self) -> None:
        python = PYTHON if PYTHON.is_file() else "python"
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src")
        env["PYTHONIOENCODING"] = "utf-8"
        proc = subprocess.Popen(
            [str(python), "-m", "illusionforge", "mcp"],
            cwd=str(ROOT),
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        assert proc.stdin and proc.stdout
        proc.stdin.write(_frame({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "0"}},
        }))
        proc.stdin.write(_frame({"jsonrpc": "2.0", "method": "notifications/initialized"}))
        proc.stdin.write(_frame({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}))
        proc.stdin.write(_frame({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "illusion_compile", "arguments": {"prompt": "koikatsu short woman", "game": "kk"}},
        }))
        proc.stdin.close()
        try:
            init = _read(proc.stdout)
            tools = _read(proc.stdout)
            compiled = _read(proc.stdout)
        finally:
            proc.stdout.close()
            proc.wait(timeout=20)
        self.assertEqual(init["result"]["serverInfo"]["name"], "illusionforge")
        names = [tool["name"] for tool in tools["result"]["tools"]]
        self.assertIn("illusion_apply", names)
        self.assertIn("illusion_bridge", names)
        body = json.loads(compiled["result"]["content"][0]["text"])
        self.assertEqual(body["game"], "kk")
        self.assertEqual(body["body_sliders"]["height"], 0.25)
        self.assertFalse(compiled["result"]["isError"])
        self.assertEqual(proc.returncode, 0)
