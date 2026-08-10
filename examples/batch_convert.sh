#!/bin/bash
# batch_convert.sh - Batch convert GLB files to FBX

INPUT_DIR="${1:-examples/input}"
OUTPUT_DIR="${2:-examples/output/batch_$(date +%Y%m%d)}"

mkdir -p "$OUTPUT_DIR"

for glb in "$INPUT_DIR"/*.glb; do
  [ -f "$glb" ] || continue
  base=$(basename "$glb" .glb)
  echo "Converting $base..."
  ./bin/glb_to_fbx.sh "$glb" "$OUTPUT_DIR/$base.fbx"
done

echo "Batch complete: $OUTPUT_DIR/"
