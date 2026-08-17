#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Structural validation for text-to-3d-asset pipeline artifacts.

Catches "the file exists but is garbage" failures without opening a 3D viewer —
the scriptable version of SKILL.md's "preview the GLB" step. Pure stdlib.

  python3 scripts/validate_outputs.py image.png [model.glb [model.fbx ...]]

Exit code 0 = every file passed; 1 = at least one failure; 2 = usage error.
Checks:
  .png  PNG signature + IHDR chunk (width/height > 0)
  .glb  12-byte GLB header (magic glTF, version 2, length matches file size),
        JSON chunk parses, reports meshes / materials / images / buffer sizes
  .fbx  'Kaydara FBX Binary' magic + version field (Blender >= 7400 -> 7.4)
"""
import json
import struct
import sys

FAILURES = 0


def ok(msg):
    print(f"  [ OK ] {msg}")


def bad(msg):
    global FAILURES
    FAILURES += 1
    print(f"  [FAIL] {msg}")


def check_png(path, data):
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        bad(f"{path}: missing PNG signature")
        return
    # first chunk must be IHDR
    if len(data) < 33 or data[12:16] != b"IHDR":
        bad(f"{path}: first chunk is not IHDR")
        return
    w, h = struct.unpack(">II", data[16:24])
    if w == 0 or h == 0:
        bad(f"{path}: zero-size image ({w}x{h})")
        return
    ok(f"{path}: PNG {w}x{h}, {len(data)/1024:.0f} KB")


def check_glb(path, data):
    if len(data) < 12 or data[:4] != b"glTF":
        bad(f"{path}: not a GLB (bad magic)")
        return
    version, length = struct.unpack("<II", data[4:12])
    if version != 2:
        bad(f"{path}: GLB version {version} (expected 2)")
        return
    if length != len(data):
        bad(f"{path}: header length {length} != file size {len(data)} (truncated write?)")
        return
    # chunk 0: JSON
    jlen, jtype = struct.unpack("<II", data[12:20])
    if jtype != 0x4E4F534A:  # 'JSON'
        bad(f"{path}: first chunk is not JSON")
        return
    try:
        doc = json.loads(data[20:20 + jlen])
    except ValueError as e:
        bad(f"{path}: JSON chunk does not parse: {e}")
        return
    meshes = doc.get("meshes", [])
    prims = sum(len(m.get("primitives", [])) for m in meshes)
    mats = doc.get("materials", [])
    images = doc.get("images", [])
    total_verts = 0
    accessors = doc.get("accessors", [])
    for m in meshes:
        for p in m.get("primitives", []):
            ai = p.get("attributes", {}).get("POSITION")
            if ai is not None and ai < len(accessors):
                total_verts += accessors[ai].get("count", 0)
    if not meshes or total_verts == 0:
        bad(f"{path}: no mesh geometry in JSON chunk")
        return
    bin_len = 0
    off = 20 + jlen
    if off + 8 <= len(data):
        blen, btype = struct.unpack("<II", data[off:off + 8])
        if btype == 0x004E4942:  # 'BIN'
            bin_len = blen
    ok(f"{path}: GLB v2 — {len(meshes)} mesh(es), {prims} primitive(s), "
       f"{total_verts} verts, {len(mats)} material(s), {len(images)} embedded image(s), "
       f"BIN {bin_len/1024:.0f} KB, total {len(data)/1024:.0f} KB")
    if len(mats) > 0 and len(images) == 0:
        print(f"  [warn] {path}: has materials but no embedded images (untextured?)")


def check_fbx(path, data):
    if not data.startswith(b"Kaydara FBX Binary"):
        bad(f"{path}: missing 'Kaydara FBX Binary' magic (not an FBX?)")
        return
    # bytes 23..26 = version uint32 (7400 = FBX 7.4, what Blender exports)
    if len(data) >= 27:
        version = struct.unpack("<I", data[23:27])[0]
        ok(f"{path}: FBX binary, format {version/100:.1f}, {len(data)/1024:.0f} KB")
    else:
        bad(f"{path}: FBX truncated at {len(data)} bytes")


CHECKS = {".png": check_png, ".glb": check_glb, ".fbx": check_fbx}


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: validate_outputs.py <file.png|file.glb|file.fbx> [...]")
    import os
    for path in sys.argv[1:]:
        ext = os.path.splitext(path)[1].lower()
        if not os.path.isfile(path):
            bad(f"{path}: file not found")
            continue
        check = CHECKS.get(ext)
        if check is None:
            bad(f"{path}: unknown extension {ext!r} (expected one of {sorted(CHECKS)})")
            continue
        with open(path, "rb") as f:
            check(path, f.read())
    if FAILURES:
        print(f"validate_outputs: {FAILURES} failure(s)")
        sys.exit(1)
    print("validate_outputs: all artifacts valid")


if __name__ == "__main__":
    main()
