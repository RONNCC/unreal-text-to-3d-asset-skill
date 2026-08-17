# MANIFEST — in-repo example/validation assets

Produced in a Linux sandbox (no GPU) by the scripts listed below.
GLB/FBX bytes are REAL Blender output (Blender 5.0.1 as the `bpy` module); renders are real Cycles CPU frames.

| File | Bytes | SHA-256 (first 16) |
|---|---|---|
| `tests/fixtures/concept.png` | 44353 | `d7d3209e1f62565d` |
| `tests/fixtures/textured_cube.glb` | 46368 | `d6fd1d8ff820c69c` |
| `examples/fixtures/boiler_gradient.png` | 44353 | `d7d3209e1f62565d` |
| `examples/fixtures/Locomotive_textured.glb` | 84532 | `8cd6bbdd25059606` |
| `examples/fixtures/Wagon_textured.glb` | 20068 | `326039084bd0ac3b` |
| `examples/fixtures/fbx/Locomotive_textured.fbx` | 82188 | `d7cc5f191ce5c519` |
| `examples/fixtures/fbx/Wagon_textured.fbx` | 22812 | `e4a9de4c985c704b` |
| `docs/images/example_locomotive.png` | 343085 | `dae8be7dc618ec29` |
| `docs/images/example_wagon.png` | 324369 | `e3dc6c74615a79b4` |
| `docs/images/example_cube.png` | 324897 | `f581cf3ced0389ea` |

## How each file was produced

| File | Produced by |
|---|---|
| `tests/fixtures/concept.png` | `python3 tests/fixtures/make_fixtures.py` (pure-Python PNG writer) |
| `tests/fixtures/textured_cube.glb` | same — hand-assembled glTF 2.0 binary, PNG embedded |
| `examples/fixtures/boiler_gradient.png` | same writer, reused via `build_examples.py` |
| `examples/fixtures/*_textured.glb` | `examples/fixtures/build_examples.py` (procedural meshes via bpy, exported with Blender's glTF exporter) |
| `examples/fixtures/fbx/*.fbx` | the repo's real `scripts/glb_to_fbx.py` run inside Blender 5.0.1 (`bpy` module) — the Dockerfile uses Blender 4.0.2, same operators |
| `docs/images/example_*.png` | `examples/fixtures/render_preview.py` — Cycles CPU renders of the GLBs above |

These stand in for Hunyuan3D-2/Fooocus outputs so stages after the AI models are
testable anywhere. The AI stages themselves are HTTP clients; their real outputs
are shown in `docs/demo.gif` (upstream run).

Regenerate everything: `bash tests/mock_e2e.sh` + the commands above.
