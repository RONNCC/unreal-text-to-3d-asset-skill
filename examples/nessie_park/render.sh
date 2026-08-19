#!/usr/bin/env bash
# Build + render "Nessie's Lagoon" and export the GLB.
#
# This repo's bpy wheel (Blender 5) links against a few GUI shared libraries
# (libXrender, libXi, libXfixes, libICE, libSM, libGL, libxkbcommon) that are
# not present in the minimal sandbox and are never called in background/headless
# mode. We satisfy the loader with tiny stub shared objects in .stublibs/ and
# put bpy's own bundled libraries (USD, OpenImageIO, OpenColorIO, TBB, ...) on
# LD_LIBRARY_PATH. On a normal machine with a real Blender install none of this
# is needed — just run `blender --background --python build_park.py`.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"

BPYLIB="$REPO/.venv/lib/python3.11/site-packages/bpy/lib"
PY="$REPO/.venv/bin/python3"

if [ -d "$REPO/.stublibs" ]; then
  export LD_LIBRARY_PATH="$REPO/.stublibs:$BPYLIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi

exec "$PY" -u "$HERE/build_park.py" "$@"
