# Validation record — what actually works, and how that was established

This repo makes a bigger claim than most skill repos: *the pipeline has been
executed, not just written down.* Two environments did the proving:

| Environment | What it has | What it proved |
|---|---|---|
| Upstream Windows workstation (RTX 4070 Laptop, 8 GB VRAM) | Fooocus-API, Hunyuan3D-2 gradio server, Blender 4.4, Unreal + MCP | Stages 1–4 with real AI models (2026-07-24); `docs/demo.gif` is that run |
| This repo's CI-style Linux sandbox (no GPU, no Docker) | repo clients + mock AI servers + Blender 5.0.1 (`bpy` wheel) | every HTTP contract and every post-AI byte path, 2026-08-17 |

## Bugs found in the audit (all fixed — see `docs/PLAN.md`)

1. `examples/full_pipeline.sh` called both client scripts with a `--output`
   flag that **does not exist** in either script → the example crashed in
   Stage 1 before touching a server.
2. The same script passed a *file* path to `hunyuan_gen.py --out`, which takes
   a *directory*, and Stage 3 then globbed for a filename the generator never
   produces (`model.glb` vs the real `<name>_textured.glb`).
3. `bin/glb_to_fbx.sh` resolved `./io` from the caller's CWD — run it from
   anywhere but the repo root and the container mounts a different directory
   than the one the file was copied to.
4. `hunyuan_gen.py`'s docstring claimed it works against Tencent's
   `api_server.py`; in reality it only spoke the Gradio protocol
   (`gradio_app.py`). The repo's own `Dockerfile.hunyuan` launches
   `api_server.py` — the documented container path could not have worked.
5. `Dockerfile.hunyuan` launched `api_server.py` without `--enable_tex`, so
   even a successfully built container would fail every textured request.

## What was executed in the sandbox (reproducible)

```bash
python3 -m venv .venv && .venv/bin/pip install requests bpy   # +X-stub libs, see PLAN.md
.venv/bin/python tests/run_tests.py       # 6 tests, all green
PYTHON=.venv/bin/python bash tests/mock_e2e.sh   # prompt -> png -> glb -> fbx, validated
```

- **T1–T2** the two client scripts complete real HTTP round-trips against
  byte-faithful mocks (`tests/mock_servers/`) and write valid PNG/GLB.
- **T3** `--server auto` picks the FastAPI protocol from `/openapi.json`.
- **T4** `--server gradio` without `gradio_client` fails with an actionable
  one-liner, not a traceback.
- **T5** the repo's actual `scripts/glb_to_fbx.py` (run unmodified inside
  Blender's `bpy` module — the same operators the Docker image uses) converts
  the textured fixture GLB → FBX 7.4 with the PNG texture embedded.
- **T6** `scripts/validate_outputs.py` green across every artifact.
- **mock_e2e** the user-facing `examples/full_pipeline.sh` ran start-to-finish
  (real HTTP stages against mocks, real Blender stage via bpy) in ~1.5 s.
- **Renders** `docs/images/example_*.png` are Cycles CPU renders *of the
  committed GLB files*, proving they load as textured geometry.

## Not validated here (stated honestly)

- **The AI models themselves** — Fooocus and Hunyuan3D-2 need a CUDA GPU; this
  sandbox has none. Their client contracts are pinned by mocks mirroring
  `Fooocus-API`'s `text-to-image` response and Hunyuan's `api_server.py`
  `/generate` JSON contract (read from upstream source, not guessed).
- **`gradio_app.py` mode of `hunyuan_gen.py`** — unchanged from the upstream
  code that was validated on Windows; re-testing it needs a live Gradio GPU
  server (gradio_client version drift is the main risk).
- **Apple Silicon specifics** (qemu-emulated amd64 images, MPS fallbacks) —
  no ARM Mac in the sandbox; the README's honesty notes stand.
- **Unreal MCP import (Stage 4)** — needs a running Unreal editor; unchanged
  from the upstream-validated recipe. The FBX it consumes is validated (7.4
  binary, embedded textures).
- **`Dockerfile.hunyuan` image build** — no Docker daemon here; it is a
  best-effort CUDA build and still labeled as such (now with `--enable_tex` so
  its API contract matches the client).

## Sandbox parity note

The Docker image runs **Blender 4.0.2**; the sandbox ran **Blender 5.0.1**.
Both expose `bpy.ops.import_scene.gltf` / `export_scene.fbx` with the argument
names `scripts/glb_to_fbx.py` uses, and 5.x is *stricter* about glTF/FBX data
— a conversion passing here is very likely to pass in 4.0.2. If the container
ever diverges, `bin/glb_to_fbx.sh` (docker runner) plus
`bin/glb_to_fbx.sh` (bpy runner) exercise the same script file, so CI coverage
remains meaningful.
