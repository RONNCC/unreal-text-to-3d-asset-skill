#!/bin/bash
# full_pipeline.sh - End-to-end text prompt → FBX for Unreal via Docker
#
# ========================================================================
# HOW THIS WAS DONE
# ========================================================================
# The Unreal Game Assets skill converts a text prompt into a game-ready FBX
# through three stages. On macOS, Stages 1-2 require Linux/amd64 images (CUDA
# for Fooocus/Hunyuan) which Docker runs under emulation — slow but functional.
# Stage 3 (Blender GLB→FBX) runs natively on Apple Silicon via headless Blender.
#
# DOCKERFILES & SERVICES USED:
#   • docker-compose.yml  → defines services: fooocus, hunyuan, blender-fbx
#   • Dockerfile.blender  → builds 'unreal-skill-blender:4.0' (Ubuntu 24.04 + Blender 4.0.2)
#   • Dockerfile.hunyuan  → builds 'unreal-skill-hunyuan:best-effort' (CUDA 12.1, UNVALIDATED on Mac)
#   • konieshadow/fooocus-api:latest  → public amd64 image for Fooocus SDXL (pulled, not built)
#
# EXACT COMMANDS A USER RUNS:
#   1. Build Blender image (once):
#        docker compose build blender-fbx
#   2. Start Fooocus (Stage 1, background):
#        docker compose up -d fooocus
#        # wait for http://localhost:8888 to be ready (~30-60s on emulated CPU)
#   3. (Optional) Start Hunyuan locally — NOT RECOMMENDED on Mac (no GPU):
#        docker compose --profile optional up -d hunyuan
#        # Prefer remote: export HUNYUAN_URL=http://<gpu-host>:8080 and skip this.
#   4. Run the pipeline (this script):
#        bash examples/full_pipeline.sh "your prompt here"
#   5. Cleanup:
#        docker compose down
#
# VOLUME MOUNT CONVENTION (see docker-compose.yml):
#   • ./io  → /io  (read/write)  — pipeline input/output files
#   • ./scripts → /scripts (read-only) — conversion scripts
#   • ./input, ./output → NOT used by compose; local dirs for this script
#
# APPLE SILICON NOTES:
#   - Fooocus & Hunyuan images are linux/amd64 → run under QEMU emulation → SLOW.
#   - No GPU passthrough on Mac for these CUDA containers.
#   - For production: run Fooocus/Hunyuan on a Linux/NVIDIA host and set
#     FOOCUS_URL / HUNYUAN_URL to point at those remote endpoints.
#   - Blender conversion IS native and fast on Apple Silicon.
# ========================================================================

set -euo pipefail

PROMPT="${1:-a tissue engineering scaffold, porous, PCL, biodegradable, isometric view}"
OUT_DIR="examples/output/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUT_DIR"

# -------------------------------------------------------------------------
# Stage 1: Text → Image via Fooocus (docker compose service)
# -------------------------------------------------------------------------
echo "[1/3] Generating image from prompt via Fooocus container..."
# Use the running fooocus service (started via 'docker compose up -d fooocus')
# or a remote FOOCUS_URL. The service exposes port 8888.
FOOCUS_URL="${FOOCUS_URL:-http://localhost:8888}"
echo "    Using FOOCUS_URL=$FOOCUS_URL"

python3 scripts/fooocus_gen.py \
  --prompt "$PROMPT" \
  --output "$OUT_DIR/image.png" \
  --url "$FOOCUS_URL"

# -------------------------------------------------------------------------
# Stage 2: Image → 3D (GLB) via Hunyuan3D-2
# -------------------------------------------------------------------------
echo "[2/3] Generating 3D model from image via Hunyuan container..."
# Prefer remote Hunyuan (GPU) on Mac. Local container is best-effort CUDA.
HUNYUAN_URL="${HUNYUAN_URL:-http://localhost:8080}"
echo "    Using HUNYUAN_URL=$HUNYUAN_URL"

python3 scripts/hunyuan_gen.py \
  --image "$OUT_DIR/image.png" \
  --output "$OUT_DIR/model.glb" \
  --url "$HUNYUAN_URL"

# -------------------------------------------------------------------------
# Stage 3: GLB → FBX via headless Blender (docker compose run)
# -------------------------------------------------------------------------
echo "[3/3] Converting GLB → FBX via Blender container..."
# 'docker compose run --rm blender-fbx' mounts ./io at /io.
# Copy GLB into ./io, run conversion, copy FBX back.
mkdir -p io
cp "$OUT_DIR/model.glb" io/model.glb

docker compose run --rm blender-fbx \
  --background --python /scripts/glb_to_fbx.py \
  -- --src /io/model.glb --dst /io/model.fbx

cp io/model.fbx "$OUT_DIR/model.fbx"
rm -f io/model.glb io/model.fbx

echo "Done! Output in $OUT_DIR/"
ls -la "$OUT_DIR/"
