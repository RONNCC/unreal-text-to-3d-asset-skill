# Remediation & Validation Plan — line by line

Goal: make this repo genuinely work end-to-end, not just look plausible. Every item below is
traceable: **what** changes, **which line/file**, **why**, and **how it is validated**.

Status legend: `[x]` done · `[~]` done with caveat (see note) · `[ ]` pending

---

## Phase 0 — Recon (what the repo is *supposed* to do)

- [x] **0.1** `git clone` the upstream source `LaurentiuGabriel/unreal-game-assets-creation-skill`
      to `/tmp/upstream-skill` and `diff` every shared file against this repo.
      - Result: the three `scripts/*.py` are faithful ports (Windows paths → macOS/env vars).
        Logic unchanged. The regressions are all in **new** files added by this fork
        (`examples/*.sh`, `bin/glb_to_fbx.sh`, `Dockerfile.hunyuan`, docs).
- [x] **0.2** `git clone` `Tencent-Hunyuan/Hunyuan3D-2` (sparse) and read `api_server.py` +
      `gradio_app.py` to pin down the exact server contracts this repo claims to support.
      - `gradio_app.py`: `generation_all(caption, image, mv_front, mv_back, mv_left, mv_right,
        steps, guidance_scale, seed, octree_resolution, check_box_rembg, num_chunks,
        randomize_seed)` → 5-tuple `(white_glb_update, textured_glb_update, html, stats, seed)`.
        `shape_generation(...)` → 4-tuple. The existing `hunyuan_gen.py` predict call matches.
      - `api_server.py`: FastAPI. `POST /generate`, JSON body `{image: <base64>, seed,
        octree_resolution, num_inference_steps, guidance_scale, texture: bool, type: "glb"}` →
        binary GLB `FileResponse`. Default port **8081**. Texture requires the server be
        launched with `--enable_tex` (else `self.pipeline_tex` never exists → textured
        requests crash server-side). `/openapi.json` is served by FastAPI → usable for
        auto-detection.
- [x] **0.3** Probe this sandbox: no Docker; apt locked to a 284-package subset (no blender,
      no X libs); GitHub + PyPI reachable; sudo present.
- [x] **0.4** Establish a Blender runtime in-sandbox anyway: `pip install bpy` (Blender 5.0.1
      as a Python module, cp311) + compile stub shared objects for the 7 missing GUI libs
      (`libGL.so.1`, `libICE.so.6`, `libSM.so.6`, `libXfixes.so.3`, `libXi.so.6`,
      `libXrender.so.1`, `libxkbcommon.so.0` — headless background mode never calls into them).
      Confirms `bpy.ops.import_scene.gltf` and `bpy.ops.export_scene.fbx` both exist.
      → Stage 3 can be **really** validated here, zero GPU needed.

## Phase 1 — Bug fixes (audit findings, each verifiable)

| # | File / line (at audit time) | Defect | Fix |
|---|-----------------------------|--------|-----|
| 1 | `examples/full_pipeline.sh:62` | calls `fooocus_gen.py --output` — argparse has **no** `--output` (only `--out`) → Stage 1 crashes with `unrecognized arguments` | `--out "$OUT_DIR/image.png"` |
| 2 | `examples/full_pipeline.sh:74-77` | calls `hunyuan_gen.py --output "$OUT_DIR/model.glb"` — **no** `--output` flag, and `--out` is a *directory*, not a file | `--out "$OUT_DIR" --name model` |
| 3 | `examples/full_pipeline.sh:82-90` | Stage 3 consumes `$OUT_DIR/model.glb`, but `hunyuan_gen.py` writes `<name>_textured.glb` → file-not-found | consume `"$OUT_DIR/model_textured.glb"` |
| 4 | `examples/full_pipeline.sh:56` | default prompt is an off-domain tissue-engineering leftover (demo/README use a locomotive) | locomotive default; biomedical prompts stay in `sample_prompts.txt` under their own section |
| 5 | `bin/glb_to_fbx.sh:19` | `IO_DIR="$(pwd)/io"` is computed **before** the `cd` to the repo root, so running the script from any other directory copies the GLB into the wrong place while compose mounts the repo's `./io` → container "file not found" | compute `REPO_ROOT` first; `IO_DIR="${IO_DIR:-$REPO_ROOT/io}"`; portable repo-root resolution (no `realpath` assumption) |
| 6 | `scripts/hunyuan_gen.py` (whole file) | docstring claims it "works against Tencent's official api_server.py" — false: `gradio_client` only speaks the Gradio protocol; `api_server.py` is FastAPI with a JSON binary-response contract. Running the documented Docker path (`Dockerfile.hunyuan` → `api_server.py`) **cannot** work with this client | add `--server {auto,gradio,api}`: `api` mode posts `{image: base64, ...}` to `/generate` via `requests` and saves the GLB bytes; `auto` probes `/openapi.json`; lazy-import `gradio_client` so `api` mode needs only `requests` |
| 7 | `Dockerfile.hunyuan:33` | `CMD` omits `--enable_tex` → the container can never generate textured meshes (server-side crash on `texture:true`), which is this skill's default mode | add `--enable_tex` to `CMD` |
| 8 | `README.md` quick start | duplicate `export HUNYUAN_URL=...` lines; `cd unreal-game-assets-creation-skill-mac` is not this repo's folder name | fix both; link `docs/EXAMPLES.md` / `docs/VALIDATION.md` |
| 9 | `.gitignore` | `examples/output/` batches are not ignored (only top-level `output/` is) — first example script run dirties the tree | ignore `examples/output/*` but keep `.gitkeep`; also ignore `.venv/` |
| 10 | `requirements.txt` | undocumented pins; `gradio_client` should read as "only for gradio mode" | keep deps, annotate when each is needed |

## Phase 2 — Validation infrastructure (no GPU required)

- [x] **2.1** `scripts/validate_outputs.py` — structural validator for pipeline artifacts:
      PNG (signature + IHDR), GLB (magic/JSON chunk/BIN chunk, mesh count, material/texture
      count, byte sizes), FBX (`Kaydara FBX Binary` magic). Exit non-zero on failure.
      This is the scriptable version of SKILL.md's "preview the GLB" step.
- [x] **2.2** `tests/mock_servers/mock_fooocus.py` — stdlib HTTP mock of Fooocus-API:
      `POST /v1/generation/text-to-image` → `[{"url": "/files/gen.png", "seed": N,
      "finish_reason": "SUCCESS"}]`; `GET /files/gen.png` → a deterministic generated PNG.
- [x] **2.3** `tests/mock_servers/mock_hunyuan_api.py` — stdlib mock of `api_server.py`:
      `GET /openapi.json` → 200; `POST /generate` → 200 binary GLB built from a deterministic
      fixture (and asserts the request carried base64 image + `texture` flag).
- [x] **2.4** `tests/fixtures/make_fixtures.py` — pure-Python deterministic fixture builder:
      a PNG "concept image" (zip-compressed PNG writer, no deps) and a textured GLB
      (glTF 2.0 JSON + BIN chunk + embedded PNG texture — hand-assembled, validated against
      the spec by re-importing in Blender).
- [x] **2.5** `tests/run_tests.py` — unittest suite (stdlib + `requests` only):
      1. `fooocus_gen.py` vs mock → PNG written + `validate_outputs.py` passes.
      2. `hunyuan_gen.py --server api` vs mock → GLB written + validated.
      3. `hunyuan_gen.py --server auto` detects the API mock without a gradio install.
      4. `hunyuan_gen.py --server gradio` without `gradio_client` → clean, actionable error
         (no traceback dump).
      5. Full mock chain: mock-image → mock-GLB → real `glb_to_fbx.py` inside `bpy` →
         validated FBX with an embedded texture.
- [x] **2.6** `tests/run_blender_convert.py` — adapter that runs `scripts/glb_to_fbx.py`
      inside the `bpy` module unmodified (same code path the Docker image executes).

## Phase 3 — Real example assets produced in this sandbox

- [x] **3.1** `examples/fixtures/build_examples.py` — builds small, textured, low-poly
      stand-in assets (boxy "asset pack" meshes with baked vertex-color + image texture)
      via `bpy`, exports them as GLB exactly where a real Hunyuan run would write them.
      Clearly labeled as *synthetic stand-ins* for the GPU stages — they exercise every
      downstream byte exactly like the real thing (same importer/exporter/validator).
- [x] **3.2** Convert each fixture GLB → FBX with the **real** `scripts/glb_to_fbx.py`;
      validate every artifact with `validate_outputs.py`; record SHA-256 + sizes in a
      `examples/fixtures/MANIFEST.md`.
- [x] **3.3** CPU-render at least one turntable/preview frame (Cycles, no GPU/GL context
      needed) into `docs/images/` so EXAMPLES.md shows an *actual* mesh produced and
      processed by this repo, not a mock screenshot.

## Phase 4 — Docs: examples of text in → assets out

- [x] **4.1** This file (`docs/PLAN.md`).
- [x] **4.2** `docs/EXAMPLES.md` — the gallery:
      - Example A: the **real upstream run** (prompt → Fooocus image → Hunyuan GLB →
        turntable `docs/demo.gif`), with the exact prompt and the exact commands.
      - Example B-D: copy-paste recipes (locomotive / wagon / signal prop + one
        biomedical cross-domain): prompt text, stage-by-stage commands, artifact names,
        expected sizes, and timings — each figure explicitly labeled
        `[measured on upstream RTX 4070]` vs `[sandbox validation]`.
      - The sandbox-produced fixtures table (real GLB/FBX bytes, checksums).
- [x] **4.3** `docs/VALIDATION.md` — what was executed where: this sandbox (client↔mock
      e2e, GLB→FBX via real Blender code path, structure checks), upstream (GPU stages),
      and what remains unvalidated (Apple Silicon, compose build of `Dockerfile.hunyuan`,
      Unreal MCP import — with reasons).
- [x] **4.4** `README.md` — corrected quick start, new "Examples" and "Validation" sections,
      updated Contents block (new scripts/tests/docs listed).
- [x] **4.5** `SKILL.md` — Stage 2 documents `--server auto|gradio|api` and the
      `api_server.py` vs `gradio_app.py` distinction; validation-status paragraph refreshed.
- [x] **4.6** `examples/sample_prompts.txt` — restructured: validated game-asset prompt
      patterns first (with the background/subject guidance baked in), biomedical set kept
      as its own clearly-labeled domain section, plus style-modifier appendix.
- [x] **4.7** `examples/full_pipeline.sh` header — the "HOW THIS WAS DONE" block corrected
      to describe the fixed flags and the api/gradio server modes.

## Phase 5 — Run everything, then merge & commit

- [x] **5.1** `python3 tests/run_tests.py` green in the sandbox venv.
- [x] **5.2** Rebuild fixtures + run the fixed `examples/full_pipeline.sh` against the mock
      servers end-to-end (uses the same env-var contract as production).
- [x] **5.3** `git merge main` (no-op: session branch is at `main`'s HEAD) → commit all
      changes on `arena/01a00f27-unreal-text-to-3d-asset-skill` with a detailed message.
- [x] **5.4** Reply with: findings, plan, what now provably works, and what still needs a GPU.

### Explicitly out of scope (stated honestly)

- No SDXL/Hunyuan weights were run here (no GPU) — AI quality is validated by the upstream
  demo + the identical HTTP contracts, not re-generated in this sandbox.
- `Dockerfile.hunyuan` remains unbuilt (no Docker, no NVIDIA host); the client fix is
  validated against a byte-faithful mock of its HTTP contract.
