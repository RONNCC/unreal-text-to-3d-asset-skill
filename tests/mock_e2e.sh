#!/usr/bin/env bash
# mock_e2e.sh — dry-run the ENTIRE example pipeline without a GPU.
#
# Starts the mock Fooocus-API + mock Hunyuan api_server (tests/mock_servers/),
# points the standard env vars at them, and runs examples/full_pipeline.sh
# exactly as a user would — stages 1+2 hit the mocks over real HTTP, stage 3
# runs the REAL glb_to_fbx.py through whichever Blender runner is available
# (docker > blender > bpy; use LD_LIBRARY_PATH for bpy stub libs if needed).
#
# Usage:
#   PYTHON=.venv/bin/python LD_LIBRARY_PATH=/tmp/stublibs bash tests/mock_e2e.sh
set -euo pipefail
cd "$(dirname "$0")/.."   # repo root

PYTHON="${PYTHON:-python3}"
PORT_F="${PORT_F:-18888}"
PORT_H="${PORT_H:-18080}"
OUT_DIR="${OUT_DIR:-examples/output/mock_e2e}"
NAME="MockTrain"

cleanup() { [ -n "${F_PID:-}" ] && kill "$F_PID" 2>/dev/null || true
            [ -n "${H_PID:-}" ] && kill "$H_PID" 2>/dev/null || true; }
trap cleanup EXIT

echo "== starting mock servers"
"$PYTHON" tests/mock_servers/mock_fooocus.py "$PORT_F" >/tmp/mock_fooocus.log 2>&1 & F_PID=$!
"$PYTHON" tests/mock_servers/mock_hunyuan_api.py "$PORT_H" >/tmp/mock_hunyuan.log 2>&1 & H_PID=$!

for url in "http://127.0.0.1:$PORT_F/files/generated.png" "http://127.0.0.1:$PORT_H/openapi.json"; do
  for _ in $(seq 1 50); do
    curl -sf -o /dev/null "$url" && break || sleep 0.2
  done
done

echo "== running full_pipeline.sh against mocks"
FOOCUS_URL="http://127.0.0.1:$PORT_F" \
HUNYUAN_URL="http://127.0.0.1:$PORT_H" \
OUT_DIR="$OUT_DIR" NAME="$NAME" PYTHON="$PYTHON" \
  bash examples/full_pipeline.sh \
    "a tiny mocked locomotive, single centered object, plain white background"

echo "== validating artifacts"
"$PYTHON" scripts/validate_outputs.py \
  "$OUT_DIR/image.png" "$OUT_DIR/${NAME}_textured.glb" "$OUT_DIR/${NAME}_textured.fbx"

echo "MOCK E2E: PASS  ($OUT_DIR)"
