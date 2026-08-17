#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic test fixtures for the pipeline — no third-party deps.

Builds:
  concept.png        a synthetic "Stage 1" concept image (pure-Python PNG writer)
  textured_cube.glb  a hand-assembled glTF 2.0 binary (GLB): one cube, 24 verts,
                     flat normals, UVs, one material with the PNG embedded as its
                     baseColorTexture. This is byte-structurally identical in
                     shape to what Hunyuan3D-2's exporter writes (glb, meshes +
                     embedded image), so downstream stages exercise the real
                     importer/exporter/validator code paths.

Regenerate:  python3 tests/fixtures/make_fixtures.py
"""
import json
import os
import struct
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------------------
# PNG (minimal encoder: 8-bit RGB, filter 0 scanlines, zlib deflate)
# ---------------------------------------------------------------------------
def write_png(path, width=256, height=256):
    def px(x, y):
        # deterministic gradient + border, plausibly "concept art" sized
        if x < 8 or y < 8 or x >= width - 8 or y >= height - 8:
            return (30, 30, 34)                       # dark border
        r = 40 + (x * 160) // width
        g = 90 + (y * 120) // height
        b = 200 - (x * 80) // width
        return (r, g, b)

    raw = b"".join(
        b"\x00" + b"".join(bytes(px(x, y)) for x in range(width))
        for y in range(height)
    )

    def chunk(tag, payload):
        c = tag + payload
        return struct.pack(">I", len(payload)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)  # 8-bit, truecolor
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
           + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)
    return png


# ---------------------------------------------------------------------------
# GLB (glTF 2.0): single textured cube
# ---------------------------------------------------------------------------
# 6 faces x 4 corners; per-face flat normals; uv corners (0,0),(1,0),(1,1),(0,1)
FACES = [
    # normal      corners (counter-clockwise seen from outside)
    ((0, 0, 1),  [(-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)]),
    ((0, 0, -1), [(1, -1, -1), (-1, -1, -1), (-1, 1, -1), (1, 1, -1)]),
    ((1, 0, 0),  [(1, -1, 1), (1, -1, -1), (1, 1, -1), (1, 1, 1)]),
    ((-1, 0, 0), [(-1, -1, -1), (-1, -1, 1), (-1, 1, 1), (-1, 1, -1)]),
    ((0, 1, 0),  [(-1, 1, 1), (1, 1, 1), (1, 1, -1), (-1, 1, -1)]),
    ((0, -1, 0), [(-1, -1, -1), (1, -1, -1), (1, -1, 1), (-1, -1, 1)]),
]
UVS = [(0, 1), (1, 1), (1, 0), (0, 0)]


def build_cube_glb(png_bytes):
    positions, normals, uvs, indices = [], [], [], []
    for fi, (n, corners) in enumerate(FACES):
        for ci, corner in enumerate(corners):
            positions.append(corner)
            normals.append(n)
            uvs.append(UVS[ci])
        base = fi * 4
        indices += [base, base + 1, base + 2, base, base + 2, base + 3]

    buf = b""
    views = []

    def push(blob):
        nonlocal buf
        pad = (-len(buf)) % 4                      # 4-byte align each view
        buf += b"\x00" * pad
        off = len(buf)
        buf += blob
        views.append((off, len(blob)))

    push(b"".join(struct.pack("<3f", *p) for p in positions))
    push(b"".join(struct.pack("<3f", *n) for n in normals))
    push(b"".join(struct.pack("<2f", *t) for t in uvs))
    push(b"".join(struct.pack("<H", i) for i in indices))
    push(png_bytes)

    gltf = {
        "asset": {"version": "2.0", "generator": "unreal-text-to-3d-asset-skill fixture"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": "fixture_cube"}],
        "meshes": [{"name": "fixture_cube", "primitives": [{
            "attributes": {"POSITION": 0, "NORMAL": 1, "TEXCOORD_0": 2},
            "indices": 3, "material": 0,
        }]}],
        "materials": [{"name": "fixture_mat", "pbrMetallicRoughness": {
            "baseColorTexture": {"index": 0}, "metallicFactor": 0.0, "roughnessFactor": 0.9}}],
        "textures": [{"source": 0, "sampler": 0}],
        "images": [{"mimeType": "image/png", "bufferView": 4}],
        "samplers": [{"magFilter": 9729, "minFilter": 9987}],
        "accessors": [
            {"bufferView": 0, "componentType": 5126, "count": len(positions), "type": "VEC3",
             "min": [-1, -1, -1], "max": [1, 1, 1]},
            {"bufferView": 1, "componentType": 5126, "count": len(normals), "type": "VEC3"},
            {"bufferView": 2, "componentType": 5126, "count": len(uvs), "type": "VEC2"},
            {"bufferView": 3, "componentType": 5123, "count": len(indices), "type": "SCALAR"},
        ],
        "bufferViews": [
            {"buffer": 0, "byteOffset": off, "byteLength": ln} for off, ln in views],
        "buffers": [{"byteLength": len(buf)}],
    }

    js = json.dumps(gltf, separators=(",", ":")).encode()
    js += b" " * ((-len(js)) % 4)                  # JSON chunk padded with spaces
    buf += b"\x00" * ((-len(buf)) % 4)             # BIN chunk padded with zeros
    total = 12 + 8 + len(js) + 8 + len(buf)
    glb = (struct.pack("<III", 0x46546C67, 2, total)     # magic 'glTF', v2, total len
           + struct.pack("<II", len(js), 0x4E4F534A) + js   # 'JSON'
           + struct.pack("<II", len(buf), 0x004E4942) + buf)  # 'BIN'
    return glb


def main():
    png = write_png(os.path.join(HERE, "concept.png"))
    glb = build_cube_glb(png)
    with open(os.path.join(HERE, "textured_cube.glb"), "wb") as f:
        f.write(glb)
    print(f"fixtures: concept.png {len(png)} B, textured_cube.glb {len(glb)} B")


if __name__ == "__main__":
    main()
