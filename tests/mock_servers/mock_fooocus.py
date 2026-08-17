#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mock Fooocus-API server (konieshadow/fooocus-api), stdlib only.

Implements exactly the two HTTP interactions scripts/fooocus_gen.py performs:
  POST /v1/generation/text-to-image
      accepts the JSON payload, echoes a generated-file record:
      [{"url": "/files/generated.png", "seed": <int>, "finish_reason": "SUCCESS"}]
  GET  /files/generated.png
      serves a real, validated PNG (tests/fixtures/concept.png)

Usage: mock_fooocus.py [port]      (default port 0 = ephemeral; prints the bound port)
"""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fixtures", "concept.png")


class Handler(BaseHTTPRequestHandler):
    server_version = "MockFooocusAPI/1.0"

    def log_message(self, *a):  # quiet
        pass

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/v1/generation/text-to-image":
            return self._json(404, {"detail": "not found"})
        n = int(self.headers.get("Content-Length", 0))
        payload = json.loads(self.rfile.read(n) or b"{}")
        if not payload.get("prompt"):
            return self._json(422, {"detail": "prompt required"})
        self._json(200, [{
            "url": "/files/generated.png",
            "seed": payload.get("image_seed", 1) if payload.get("image_seed", -1) != -1 else 42,
            "finish_reason": "SUCCESS",
        }])

    def do_GET(self):
        if self.path != "/files/generated.png":
            self.send_response(404)
            self.end_headers()
            return
        with open(FIXTURE, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"mock_fooocus on :{srv.server_address[1]}", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
