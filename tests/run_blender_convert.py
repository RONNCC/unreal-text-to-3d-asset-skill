#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run the repo's REAL scripts/glb_to_fbx.py inside the `bpy` Python module.

This is the sandbox equivalent of what Dockerfile.blender does:

    blender --background --python /scripts/glb_to_fbx.py -- --src X.glb --dst Y.fbx

The conversion script itself is executed unmodified (runpy.run_path), so the
exact GLB->FBX code path ships in the Docker image is what gets tested here.

Usage:
    LD_LIBRARY_PATH=<stub libs, if needed> python3 tests/run_blender_convert.py \
        --src input.glb --dst output.fbx

Fails loudly (exit 1) if bpy is unavailable, so the caller can skip gracefully.
"""
import os
import runpy
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    try:
        import bpy  # noqa: F401
    except Exception as e:
        print(f"[run_blender_convert] bpy unavailable ({e}); cannot validate FBX stage here")
        sys.exit(1)

    # Blender scripts expect argv like: blender --background --python x.py -- <args>
    sys.argv = [os.path.join(REPO, "scripts", "glb_to_fbx.py"), "--"] + sys.argv[1:]
    runpy.run_path(os.path.join(REPO, "scripts", "glb_to_fbx.py"), run_name="__main__")
    print("[run_blender_convert] conversion finished OK")


if __name__ == "__main__":
    main()
