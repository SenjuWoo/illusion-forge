"""The bridge client speaks one JSON line and refuses a non-loopback host."""

from __future__ import annotations

import json
import socket
import threading
import unittest

from illusionforge.bridge.client import exchange, prepare_payload


class BridgeClientTests(unittest.TestCase):
    def test_face_names_become_indexes(self) -> None:
        payload = prepare_payload({"op": "apply", "face_sliders": {"face_width": 0.75, "3": 0.2, "nope": 0.1}})
        self.assertEqual(payload["face_sliders"]["0"], 0.75)
        self.assertEqual(payload["face_sliders"]["3"], 0.2)
        self.assertEqual(payload["face_sliders"]["nope"], 0.1)
        self.assertNotIn("face_width", payload["face_sliders"])
        ping = {"op": "ping", "face_sliders": {"face_width": 1}}
        self.assertIs(prepare_payload(ping), ping)

    def test_refuses_remote_host(self) -> None:
        with self.assertRaises(ValueError):
            exchange({"op": "ping"}, host="8.8.8.8", port=9, timeout=0.2)

    def test_roundtrip_against_a_fake_listener(self) -> None:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        port = server.getsockname()[1]

        def serve() -> None:
            conn, _addr = server.accept()
            with conn:
                data = b""
                while b"\n" not in data:
                    data += conn.recv(4096)
                payload = json.loads(data.split(b"\n", 1)[0].decode("utf-8"))
                body = json.dumps({"ok": True, "op": payload["op"], "echo": payload.get("n")}) + "\n"
                conn.sendall(body.encode("utf-8"))

        thread = threading.Thread(target=serve)
        thread.start()
        try:
            reply = exchange({"op": "ping", "n": 3}, port=port, timeout=5)
        finally:
            thread.join(timeout=5)
            server.close()
        self.assertTrue(reply["ok"])
        self.assertEqual(reply["op"], "ping")
        self.assertEqual(reply["echo"], 3)
