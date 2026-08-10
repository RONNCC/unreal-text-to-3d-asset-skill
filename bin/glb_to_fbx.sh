#!/usr/bin/env bash
# Convert a GLB to FBX (embedded textures) using the headless Blender container.
#
# Usage:
#   bin/glb_to_fbx.sh <input.glb> <output.fbx>
#
# The file is copied into ./io (mounted at /io in the container), converted, and
# copied back to the requested destination. Blender 4.x runs as a linux/amd64
# container, so this works identically on Intel and Apple Silicon Macs.
set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "usage: $0 <input.glb> <output.fbx>" >&2
  exit 2
fi

SRC="$1"
DST="$2"
IO_DIR="${IO_DIR:-$(pwd)/io}"

[ -f "$SRC" ] || { echo "error: input not found: $SRC" >&2; exit 1; }

mkdir -p "$IO_DIR" "$(dirname "$DST")"
cp "$SRC" "$IO_DIR/input.glb"

# shellcheck disable=SC2164
cd "$(dirname "$(dirname "$(realpath "$0")")")"
docker compose run --rm blender-fbx --background \
  --python /scripts/glb_to_fbx.py -- \
  --src /io/input.glb --dst "/io/$(basename "$DST")"

cp "$IO_DIR/$(basename "$DST")" "$DST"
echo "converted: $DST"
