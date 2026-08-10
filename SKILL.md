---
name: text-to-3d-asset
description: >-
  Generate a game-ready 3D asset by running the AI pipeline sequentially:
  Fooocus (SDXL text-to-image) -> Hunyuan3D-2 (image-to-textured-GLB) -> optional
  Blender FBX convert + Unreal import. Use when the user wants to create/generate
  a 3D model, mesh, or racer for the Unreal train-racer project from a text prompt
  or a photo. This is the macOS + Docker conversion: services run as containers or
  are reached over HTTP (FOOCUS_URL / HUNYUAN_URL), clients are plain python3.
---

# Text / Photo -> 3D Asset Pipeline (macOS + Docker)

Two AI services chain together to turn a **text prompt or photo** into a **textured 3D `.glb`**,
which then imports into the Unreal train-racer project. This skill is the macOS + Docker conversion
of the upstream Windows skill (see README.md). Related background: `hunyuan3d-deployment` memory.

```
prompt --(Fooocus SDXL)--> image.png --(Hunyuan3D-2)--> textured.glb --(Blender, Docker)--> .fbx --(Unreal MCP)--> BP racer
        [Stage 1: optional]            [Stage 2: core]              [Stage 3: optional, Unreal only]
```

If the user already has a photo, **skip Stage 1** and start at Stage 2.

**Validation status:** upstream validated end-to-end on Windows (2026-07-24): Stage 1 via **Fooocus-API**
REST `text-to-image`; Stage 2 (`hunyuan_gen.py`) + Stage 3 convert (`glb_to_fbx.py`) working
(image -> textured `.glb` -> `.fbx`, ~60–130 s for the 3D step); Stage 3 Unreal import validated (Caitlin).
This macOS/Docker conversion keeps the same scripts and HTTP contracts; the container build of
`Dockerfile.hunyuan` is best-effort/unvalidated (no official image exists).

## ⚠️ Apple-Silicon hardware rule — STRICT

- **Fooocus and Hunyuan3D are CUDA-oriented.** On Apple Silicon expect **CPU/MPS or a remote NVIDIA
  box**, not equal performance to the upstream RTX 4070 Laptop baseline. Generation will be slower and
  may need reduced resolutions. Honest expectation: works, but not GPU-fast locally.
- **Only one heavy generation at a time.** The upstream machine (8 GB VRAM / 32 GB RAM) measurably
  swapped when both servers were resident (~1 min -> ~14 min for SDXL). Run stages sequentially;
  stop/leave down the server you are not using.
- **Fooocus-API image is amd64-only** (`konieshadow/fooocus-api:latest`). On Apple Silicon Docker runs
  it emulated on CPU. For real speed, run it on a Linux/NVIDIA host and set `FOOCUS_URL`.
- **No official Hunyuan3D-2 image exists.** Prefer remote-service mode (below); `Dockerfile.hunyuan`
  is a best-effort CUDA/amd64 build for Linux/NVIDIA hosts only.

## Key paths (macOS convention)

| Thing | Path |
|---|---|
| Skill scripts | this skill's `scripts/` folder |
| Python venv (client deps) | `~/AI/venv` (`python3 -m venv ~/AI/venv`) |
| Image / GLB / FBX outputs | `~/AI/outputs` |
| Docker compose file | this repo's `docker-compose.yml` |
| Blender container helper | `bin/glb_to_fbx.sh` |
| Fooocus-API endpoint | `http://localhost:8888` — `POST /v1/generation/text-to-image` (`FOOCUS_URL`) |
| Hunyuan3D endpoint | `http://localhost:8080` (`HUNYUAN_URL`) |
| Unreal (optional) | via the `unreal-mcp` server, e.g. `http://localhost:8899` |

No `C:\` paths anywhere — clients use python3 from the venv and Docker containers for Blender.

## Stage 0 — bring up the services (Docker)

```bash
# (optional) client deps, once
python3 -m venv ~/AI/venv && source ~/AI/venv/bin/activate && pip install -r requirements.txt

# Stage 1 service: Fooocus-API (published amd64 image; emulated/CPU on Apple Silicon)
docker compose up -d fooocus

# Stage 2 service: Hunyuan3D-2 — no official image; see remote-service mode below.
#   On a Linux/NVIDIA host you may try:  docker compose --profile optional up -d hunyuan
#   (best-effort CUDA build, NOT validated on Apple Silicon)
```

Services read their URLs from env vars, so both scripts are platform-neutral:

```bash
export FOOCUS_URL="${FOOCUS_URL:-http://localhost:8888}"
export HUNYUAN_URL="${HUNYUAN_URL:-http://localhost:8080}"
```

### Remote-service mode (recommended for Hunyuan on a Mac)

Run Hunyuan3D-2's official `api_server.py` (or the best-effort container) on any machine with an
NVIDIA GPU and point the client at it:

```bash
export HUNYUAN_URL=http://my-gpu-host:8080
export FOOCUS_URL=http://my-gpu-host:8888   # same trick for Fooocus
```

The scripts only speak HTTP — they do not care where the server runs.

## Stage 1 — Generate the image (Fooocus SDXL)

Only if starting from a text prompt. Model already handled by the image:
`juggernautXL_v8Rundiffusion` (photoreal) is the Fooocus-API default checkpoint.

**For best downstream 3D:** prompt for a *single centered subject, plain/simple background,
3/4 or front view, even lighting*. Hunyuan3D's auto background-removal expects one clear subject.
Add e.g. `, single object, centered, plain white background, studio lighting, full view`.

```bash
export FOOCUS_URL=http://localhost:8888   # or a remote GPU host
python3 scripts/fooocus_gen.py \
  --prompt "a vintage green steam locomotive, single centered object, plain white background, studio lighting, full view" \
  --out ~/AI/outputs/train.png
```

Blocks until done, saves the PNG. ~1–2 min on the upstream GPU; slower on Apple Silicon (CPU/emulation).

Either way, Stage 1 produces a PNG on disk. **Stop Fooocus-API (port 8888) before Stage 2.**

## Stage 2 — Image -> textured GLB (Hunyuan3D-2)  [core, validated upstream]

1. Ensure a server is up, locally (remote-service mode above) or on a GPU host:
   `curl -s -o /dev/null -w '%{http_code}' "$HUNYUAN_URL"` — if down, start it (docker/remote).
2. Generate (uses the running server's API — reuses loaded models):
   ```
   python3 scripts/hunyuan_gen.py --image ~/AI/outputs/train.png --name Locomotive --out ~/AI/outputs
   ```
   - `--mode textured` (default) = shape + texture (~60–75 s on upstream GPU). `--mode shape` = geometry only.
   - Output GLB(s) land in `~/AI/outputs/<AssetName>_textured.glb` (+ `_white.glb`).
   - Prints timing + output paths.
3. **Preview it** before going further: decode is only meaningful visually — open the GLB
   (macOS Quick Look previews GLB), or continue to Stage 3 and screenshot in Unreal.

## Stage 3 — Import into Unreal (optional; needs the editor + unreal-mcp running)

The unreal-mcp `StaticMeshTools.import_file` accepts **only fbx/obj**, not glb. Convert first.

1. **GLB -> FBX (embedded textures)** via the Blender container (pure CPU, works on Apple Silicon):
   ```bash
   bin/glb_to_fbx.sh ~/AI/outputs/Locomotive_textured.glb ~/AI/outputs/Locomotive_textured.fbx
   ```
   Equivalent manual call:
   ```bash
   docker compose run --rm blender-fbx --background \
     --python /scripts/glb_to_fbx.py -- \
     --src /io/Locomotive_textured.glb --dst /io/Locomotive_textured.fbx
   ```
   (the script copies the file in and out of the compose `io/` mount; or mount your own dirs).
2. **Import** (unreal-mcp): `StaticMeshTools.import_file` with
   `folder_path=/Game/Meshes/<Name>GLB`, `asset_name=<Name>`, `import_materials=true`,
   `import_textures=true`, `combine_meshes=true`. Then `AssetTools.save_assets`.
3. **Wire into a racer BP** (project convention — see `hunyuan3d-deployment` memory): racer BPs derive
   from `BP_TrainBase`; each adds a `GLBBody` StaticMeshComponent. To add a new engine, mirror
   `BP_Thomas` (single `GLBBody`, scale to length-match Thomas ≈ `1197 / mesh_local_Y_extent`,
   `relativeRotation yaw -90`, `relativeLocation.z = -mesh_local_min_z * scale` so it sits on the ground).
   Access SCS templates via `ActorTools.get_components` on the CDO
   (`/Game/Blueprints/BP_<Name>.Default__BP_<Name>_C`) -> `BP_<Name>_C:<Comp>_GEN_VARIABLE`, then
   `ObjectTools.get/set_properties`. Compile + save the Blueprint. Verify by spawning an instance and
   `EditorAppToolset.CaptureViewport` (decode per the `unreal-mcp-screenshot-extraction` memory).

## Troubleshooting
- **Hunyuan server down / not persisting**: expected across sessions — relaunch (docker/remote).
- **CUDA OOM during 3D texture** (remote/GPU hosts): another generation is running — serialize them.
- **Import rejects .glb**: convert to FBX first (Stage 3 step 1).
- **Docker pull of `konieshadow/fooocus-api` is slow/CPU-only on Apple Silicon**: expected — that
  image is amd64. Use a remote NVIDIA host and set `FOOCUS_URL`.
- **Blender import shows one mesh named `*.ply`**: normal (Hunyuan meshes carry no node name); the
  FBX still exports fine.
