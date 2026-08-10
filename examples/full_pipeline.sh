#!/bin/bash
# full_pipeline.sh - End-to-end text prompt → FBX for Unreal

set -e

PROMPT="${1:-a tissue engineering scaffold, porous, PCL, biodegradable, isometric view}"
OUT_DIR="examples/output/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUT_DIR"

echo "[1/3] Generating image from prompt..."
python3 scripts/fooocus_gen.py \
  --prompt "$PROMPT" \
  --output "$OUT_DIR/image.png" \
  --url "${FOOCUS_URL:-http://localhost:8888}"

echo "[2/3] Generating 3D model from image..."
python3 scripts/hunyuan_gen.py \
  --image "$OUT_DIR/image.png" \
  --output "$OUT_DIR/model.glb" \
  --url "${HUNYUAN_URL:-http://localhost:8080}"

echo "[3/3] Converting to FBX for Unreal..."
./bin/glb_to_fbx.sh "$OUT_DIR/model.glb" "$OUT_DIR/model.fbx"

echo "Done! Output in $OUT_DIR/"
ls -la "$OUT_DIR/"
