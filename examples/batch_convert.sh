#!/bin/bash
# batch_convert.sh - Batch convert GLB files to FBX via Blender Docker container
#
# ========================================================================
# HOW THIS WAS DONE
# ========================================================================
# This script batch-converts every *.glb in a source directory to FBX using
# the headless Blender 4.0.2 container defined in Dockerfile.blender and
# orchestrated by docker-compose.yml (service: blender-fbx).
#
# DOCKERFILES & SERVICES USED:
#   • docker-compose.yml  → service 'blender-fbx' (profile: tools)
#   • Dockerfile.blender  → builds 'unreal-skill-blender:4.0'
#       FROM ubuntu:24.04, installs blender + python3-numpy
#       ENTRYPOINT: blender --python-use-system-env
#       WORKDIR: /work
#       Volume mounts: ./io → /io:rw, ./scripts → /scripts:ro
#
# EXACT COMMANDS A USER RUNS:
#   1. Build Blender image (once):
#        docker compose build blender-fbx
#   2. Place *.glb files in ./examples/input/ (or custom INPUT_DIR)
#   3. Run batch conversion:
#        bash examples/batch_convert.sh [INPUT_DIR] [OUTPUT_DIR]
#        # INPUT_DIR defaults to examples/input
#        # OUTPUT_DIR defaults to examples/output/batch_YYYYMMDD
#   4. Find results in OUTPUT_DIR/*.fbx
#
# VOLUME MOUNT CONVENTION:
#   • ./io  → /io  (read/write) — each GLB/FBX passes through here
#   • ./scripts → /scripts (read-only) — glb_to_fbx.py conversion script
#
# APPLE SILICON NOTES:
#   - Blender runs natively on Apple Silicon (Ubuntu arm64 base image).
#   - No CUDA/GPU needed — pure CPU GLB→FBX conversion.
#   - Fast and reliable on Mac.
# ========================================================================

set -euo pipefail

INPUT_DIR="${1:-examples/input}"
OUTPUT_DIR="${2:-examples/output/batch_$(date +%Y%m%d)}"

mkdir -p "$OUTPUT_DIR"

# Ensure Blender image exists
if ! docker image inspect unreal-skill-blender:4.0 >/dev/null 2>&1; then
  echo "Building Blender image (first run only)..."
  docker compose build blender-fbx
fi

shopt -s nullglob
for glb in "$INPUT_DIR"/*.glb; do
  base=$(basename "$glb" .glb)
  echo "Converting $base..."

  # Copy GLB into ./io for the container
  mkdir -p io
  cp "$glb" "io/${base}.glb"

  # Run conversion inside Blender container
  docker compose run --rm blender-fbx \
    --background --python /scripts/glb_to_fbx.py \
    -- --src "/io/${base}.glb" --dst "/io/${base}.fbx"

  # Copy result out
  cp "io/${base}.fbx" "$OUTPUT_DIR/${base}.fbx"

  # Clean io/ for next iteration
  rm -f "io/${base}.glb" "io/${base}.fbx"

done

shopt -u nullglob

echo "Batch complete: $OUTPUT_DIR/"
ls -la "$OUTPUT_DIR/"
