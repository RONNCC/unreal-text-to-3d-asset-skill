#!/usr/bin/env bash
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
#   • Dockerfile.hunyuan  → builds 'unreal-skill-hunyuan:best-effort' (CUDA 12.1,
#                           api_server.py with --enable_tex; UNVALIDATED on Mac)
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
#
# TESTABILITY:
#   FOOCUS_URL/HUNYUAN_URL can point at the mock servers in tests/mock_servers/
#   to dry-run this entire script without a GPU (except the dockerized FBX step);
#   see docs/VALIDATION.md for the exact mock-run transcript.
# ========================================================================
set -euo pipefail

cd "$(dirname "$0")/.."   # repo root, so relative paths in compose/scripts resolve

PROMPT="${1:-a vintage green steam locomotive, single centered object, plain white background, studio product render, full side view}"
OUT_DIR="${OUT_DIR:-examples/output/$(date +%Y%m%d_%H%M%S)}"; PYTHON="${PYTHON:-python3}"
NAME="${NAME:-Asset}"
mkdir -p "$OUT_DIR"

# -------------------------------------------------------------------------
# Stage 1: Text → Image via Fooocus-API (docker compose service or remote)
# -------------------------------------------------------------------------
echo "[1/3] Generating image from prompt via Fooocus ..."
FOOCUS_URL="${FOOCUS_URL:-http://localhost:8888}"
echo "    Using FOOCUS_URL=$FOOCUS_URL"

# NB: the flag is --out (a FILE path). fooocus_gen.py has no --output option.
"$PYTHON" scripts/fooocus_gen.py \
  --prompt "$PROMPT" \
  --out "$OUT_DIR/image.png" \
  --url "$FOOCUS_URL"

# -------------------------------------------------------------------------
# Stage 2: Image → 3D (GLB) via Hunyuan3D-2
# -------------------------------------------------------------------------
echo "[2/3] Generating 3D model from image via Hunyuan3D-2 ..."
# Prefer remote Hunyuan (GPU) on Mac. Local container is best-effort CUDA.
HUNYUAN_URL="${HUNYUAN_URL:-http://localhost:8080}"
echo "    Using HUNYUAN_URL=$HUNYUAN_URL"

# NB: --out is a DIRECTORY; the GLB lands at <dir>/<NAME>_textured.glb.
# --server auto speaks gradio_app.py or api_server.py (FastAPI) transparently.
"$PYTHON" scripts/hunyuan_gen.py \
  --image "$OUT_DIR/image.png" \
  --out "$OUT_DIR" \
  --name "$NAME" \
  --server auto \
  --url "$HUNYUAN_URL"

GLB="$OUT_DIR/${NAME}_textured.glb"
[ -f "$GLB" ] || GLB="$(ls "$OUT_DIR/${NAME}"_*.glb | head -1)"   # shape mode fallback

# -------------------------------------------------------------------------
# Stage 3: GLB → FBX via headless Blender (docker compose run)
# -------------------------------------------------------------------------
echo "[3/3] Converting GLB → FBX via Blender container ..."
bin/glb_to_fbx.sh "$GLB" "$OUT_DIR/${NAME}_textured.fbx"

# -------------------------------------------------------------------------
# Verify: structural validation of every artifact produced
# -------------------------------------------------------------------------
if [ -f scripts/validate_outputs.py ]; then
  "$PYTHON" scripts/validate_outputs.py "$OUT_DIR/image.png" "$GLB" "$OUT_DIR/${NAME}_textured.fbx"
fi

echo "Done! Output in $OUT_DIR/"
ls -la "$OUT_DIR/"
