#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mock of Hunyuan3D-2's api_server.py (FastAPI), stdlib only.

Byte-faithful to the contract scripts/hunyuan_gen.py --server api/auto uses:
  GET  /openapi.json   -> 200 {"paths": {"/generate": ..., "/send": ..., "/status/{uid}": ...}}
                          (this is also how '--server auto' detects an api server)
  POST /generate       -> JSON body: {"image": "<base64>", "seed": int,
                          "octree_resolution": int, "num_inference_steps": int,
                          "guidance_scale": float, "texture": bool, "type": "glb"}
                       -> 200 body = raw GLB bytes (like api_server's FileResponse)

The GLB served is tests/fixtures/textured_cube.glb (built by make_fixtures.py).

Usage: mock_hunyuan_api.py [port]   (default port 0 = ephemeral; prints the bound port)
"""
import base64
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fixtures", "textured_cube.glb")


class Handler(BaseHTTPRequestHandler):
    server_version = "MockHunyuanAPI/uvicorn"

    def log_message(self, *a):  # quiet
        pass

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/openapi.json":
            return self._json(200, {
                "openapi": "3.1.0",
                "info": {"title": "FastAPI", "version": "0.1.0"},
                "paths": {"/generate": {"post": {}}, "/send": {"post": {}}, "/status/{uid}": {"get": {}}},
            })
        self._json(404, {"detail": "not found"})

    def do_POST(self):
        if self.path != "/generate":
            return self._json(404, {"detail": "not found"})
        n = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
            img = base64.b64decode(body["image"])
            assert img[:8] == b"\x89PNG\r\n\x1a\n", "image must be a PNG"
        except Exception as e:
            return self._json(422, {"detail": f"bad request: {e}"})
        with open(FIXTURE, "rb") as f:
            glb = f.read()
        self.send_response(200)
        # api_server.py returns FileResponse(file_path) -> binary body
        self.send_header("Content-Type", "model/gltf-binary")
        self.send_header("Content-Disposition", 'attachment; filename="result.glb"')
        self.send_header("Content-Length", str(len(glb)))
        self.end_headers()
        self.wfile.write(glb)


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"mock_hunyuan_api on :{srv.server_address[1]}", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
