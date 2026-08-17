#!/usr/bin/env bash
# Convert a GLB to FBX (embedded textures) with headless Blender.
#
# Usage:
#   bin/glb_to_fbx.sh <input.glb> <output.fbx>
#
# Three interchangeable runners (auto-detected, or force via GLB2FBX_RUNNER):
#   docker  (default) the docker-compose 'blender-fbx' service — the file is copied
#          through ./io (mounted at /io in the container). Works identically on
#          Intel and Apple Silicon Macs.
#   blender a locally installed `blender` binary (e.g. `brew install --cask blender`,
#          or any Linux box) — no Docker needed for this pure-CPU stage.
#   bpy     Blender-as-a-python-module (`pip install bpy`) via
#          tests/run_blender_convert.py — used by the sandbox/CI validation.
#
# Set GLB2FBX_RUNNER to one of the above to force a specific runner.
set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "usage: $0 <input.glb> <output.fbx>" >&2
  exit 2
fi

# Resolve the repo root from the script location (portable: no realpath needed).
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

SRC="$1"
DST="$2"

# make SRC/DST absolute before we cd, so relative CLI paths still resolve
case "$SRC" in /*) ;; *) SRC="$(pwd)/$SRC" ;; esac
case "$DST" in /*) ;; *) DST="$(pwd)/$DST" ;; esac

[ -f "$SRC" ] || { echo "error: input not found: $SRC" >&2; exit 1; }
mkdir -p "$(dirname "$DST")"

detect_runner() {
  PYTHON="${PYTHON:-python3}"
  if [ -n "${GLB2FBX_RUNNER:-}" ]; then echo "$GLB2FBX_RUNNER"; return; fi
  if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then echo docker; return; fi
  if command -v blender >/dev/null 2>&1; then echo blender; return; fi
  if "$PYTHON" -c "import bpy" >/dev/null 2>&1; then echo bpy; return; fi
  echo "error: no runner available (need docker, a local blender, or pip-install bpy)" >&2
  exit 1
}

RUNNER="$(detect_runner)"

case "$RUNNER" in
  docker)
    # ./io is what docker-compose.yml bind-mounts at /io. Default to the REPO's
    # io dir, not the caller's CWD, so the script works from anywhere.
    IO_DIR="${IO_DIR:-$REPO_ROOT/io}"
    mkdir -p "$IO_DIR"
    cp "$SRC" "$IO_DIR/input.glb"
    cd "$REPO_ROOT"
    docker compose run --rm blender-fbx --background \
      --python /scripts/glb_to_fbx.py -- \
      --src /io/input.glb --dst "/io/$(basename "$DST")"
    cp "$IO_DIR/$(basename "$DST")" "$DST"
    rm -f "$IO_DIR/input.glb" "$IO_DIR/$(basename "$DST")"
    ;;
  blender)
    blender --background \
      --python "$REPO_ROOT/scripts/glb_to_fbx.py" -- \
      --src "$SRC" --dst "$DST"
    ;;
  bpy)
    "$PYTHON" "$REPO_ROOT/tests/run_blender_convert.py" --src "$SRC" --dst "$DST"
    ;;
  *)
    echo "error: unknown GLB2FBX_RUNNER '$RUNNER' (expected docker|blender|bpy)" >&2
    exit 2
    ;;
esac

echo "converted ($RUNNER): $DST"
