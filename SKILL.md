---
name: text-to-3d-asset
description: >-
  Generate a game-ready 3D asset by running the local AI pipeline sequentially:
  Fooocus (SDXL text-to-image) -> Hunyuan3D-2 (image-to-textured-GLB) -> optional
  Blender FBX convert + Unreal import. Use when the user wants to create/generate
  a 3D model, mesh, or racer for the Unreal train-racer project from a text prompt
  or a photo. Covers launching both local Gradio services, generating, and wiring
  the result into Unreal.
---

# Text / Photo -> 3D Asset Pipeline

Two local AI services on this machine chain together to turn a **text prompt or photo**
into a **textured 3D `.glb`**, which then imports into the Unreal train-racer project.
Related background: `hunyuan3d-deployment` memory.

```
prompt --(Fooocus SDXL)--> image.png --(Hunyuan3D-2)--> textured.glb --(Blender)--> .fbx --(Unreal MCP)--> BP racer
        [Stage 1: optional]            [Stage 2: core]              [Stage 3: optional, Unreal only]
```

If the user already has a photo, **skip Stage 1** and start at Stage 2.

**Validation status (2026-07-24):** Full chain tested end-to-end. Stage 1 automated via **Fooocus-API**
(installed at `C:\AI\Fooocus-API`; REST `text-to-image` returned a clean locomotive image). Stage 2
(`hunyuan_gen.py`) + Stage 3 convert (`glb_to_fbx.py`) working (image -> textured `.glb` -> `.fbx`,
~60–130 s for the 3D step). Stage 3 Unreal import validated (Caitlin). Vanilla Fooocus is NOT drivable
via `gradio_client` — that's why the Fooocus-API wrapper exists.

## ⚠️ Hardware rule (RTX 4070 Laptop, 8 GB VRAM / 32 GB RAM) — STRICT
**Only one image/3D service loaded at a time.** Don't just avoid concurrent *generation* — don't keep
both servers *resident*. Measured 2026-07-24: running Fooocus with the Hunyuan3D server still loaded
made SDXL take **~14 min** (27 s/step) instead of ~1 min, because the two exhaust RAM and swap to disk.
So: **stop the other server before generating.** Stage 1 → stop Hunyuan (8080), run Fooocus.
Stage 2 → stop Fooocus-API (8888), run Hunyuan. Relaunching a server is cheap vs. the slowdown.

## Key paths
| Thing | Path |
|---|---|
| Fooocus | `C:\projects\unreal-game\Fooocus_win64_2-5-0` (launch `run.bat`) |
| Fooocus UI | http://localhost:7865 |
| Fooocus outputs | `C:\projects\unreal-game\Fooocus_win64_2-5-0\Fooocus\outputs\<YYYY-MM-DD>\` |
| **Fooocus-API (REST)** | `C:\AI\Fooocus-API` — isolated `python_embeded`; `config.txt` reuses models |
| Fooocus-API endpoint | http://127.0.0.1:8888 — `POST /v1/generation/text-to-image` |
| Hunyuan3D | `C:\AI\HY3D2\Hunyuan3D2_WinPortable` (launch `launch_server.bat`) |
| Hunyuan3D UI/API | http://localhost:8080 |
| Bundle python (has gradio_client) | `C:\AI\HY3D2\Hunyuan3D2_WinPortable\python_standalone\python.exe` |
| Blender | `C:\Program Files\Blender Foundation\Blender 4.4\blender.exe` |
| Skill scripts | this skill's `scripts/` folder |

---

## Stage 1 — Generate the image (Fooocus SDXL)

Only if starting from a text prompt. Model already installed: `juggernautXL_v8Rundiffusion` (photoreal).

**For best downstream 3D:** prompt for a *single centered subject, plain/simple background,
3/4 or front view, even lighting*. Hunyuan3D's auto background-removal expects one clear subject.
Add e.g. `, single object, centered, plain white background, studio lighting, full view`.

Vanilla Fooocus has no `gradio_client` API (Gradio 3.41.2, 0 named endpoints, `gr.State` generate
flow). That's why the **Fooocus-API** REST wrapper is installed — use it (Method A). UI is the fallback.

### Method A — Fooocus-API REST (installed, automated) ✅
Isolated env at `C:\AI\Fooocus-API\python_embeded` (copy of Fooocus's embedded python + fastapi/uvicorn/
sqlalchemy/colorlog/rich/chardet; its `python310._pth` was patched to add `..` and `../repositories/Fooocus`).
`config.txt` (copied from the Fooocus install) makes it reuse juggernautXL + LoRA + expansion — no re-download.

1. **Stop the Hunyuan3D server first** (hardware rule): `$c=Get-NetTCPConnection -LocalPort 8080 -State Listen -EA SilentlyContinue; if($c){Stop-Process -Id $c.OwningProcess -Force}` (relaunch it for Stage 2).
2. Launch if port 8888 isn't up (run from its dir so `./config.txt` is found):
   `cmd /c "cd /d C:\AI\Fooocus-API && python_embeded\python.exe -s main.py --skip-pip --disable-preset-download --port 8888 --host 127.0.0.1 > C:\AI\Fooocus-API\api.log 2>&1"`
   Wait for `Uvicorn running on http://127.0.0.1:8888` in `api.log` (loads SDXL, ~20–40 s).
3. Generate:
   `C:\AI\Fooocus-API\python_embeded\python.exe -s "<this skill>\scripts\fooocus_gen.py" --prompt "<subject>, single centered object, plain white background, studio lighting, full view" --out "<path\img.png>"`
   Blocks until done, saves the PNG. ~1–2 min when Fooocus has the GPU to itself (10x slower if Hunyuan is still loaded).

### Method B — Fooocus UI (fallback, manual click)
Launch `cmd /c "cd /d C:\projects\unreal-game\Fooocus_win64_2-5-0 && run.bat"` (cold start ~5–6 min;
poll **port 7865**, the log doesn't flush). Open http://localhost:7865, enter prompt, click Generate,
grab the newest PNG from `Fooocus\outputs\<date>\`.

Either way, Stage 1 produces a PNG on disk. **Stop Fooocus-API (port 8888) before Stage 2.** Pass the PNG to Stage 2.

---

## Stage 2 — Image -> textured GLB (Hunyuan3D-2)  [core, validated]

1. Ensure the server is up (it does **not** persist across sessions):
   `Invoke-WebRequest http://localhost:8080 -UseBasicParsing`. If down, launch in background:
   `cmd /c "C:\AI\HY3D2\Hunyuan3D2_WinPortable\launch_server.bat > C:\AI\HY3D2\server.log 2>&1"`
   then watch `C:\AI\HY3D2\server.log` for `Uvicorn running on http://0.0.0.0:8080` (~1–2 min; models cached).
2. Generate (uses the running server's API — reuses loaded models):
   ```
   C:\AI\HY3D2\Hunyuan3D2_WinPortable\python_standalone\python.exe -s ^
     "<this skill>\scripts\hunyuan_gen.py" --image "<path\to\image.png>" --name <AssetName>
   ```
   - `--mode textured` (default) = shape + texture (~60–75 s). `--mode shape` = geometry only (faster).
   - Output GLB(s) land in `C:\AI\HY3D2\outputs\<AssetName>_textured.glb` (+ `_white.glb`).
   - Runs as a background command if you don't want to block; it prints timing + output paths.
3. **Preview it** before going further: decode is only meaningful visually — either open the GLB,
   or continue to Stage 3 and screenshot in Unreal.

---

## Stage 3 — Import into Unreal (optional; needs the editor + unreal-mcp running)

The unreal-mcp `StaticMeshTools.import_file` accepts **only fbx/obj**, not glb. Convert first.

1. **GLB -> FBX (embedded textures)** via Blender:
   ```
   "C:\Program Files\Blender Foundation\Blender 4.4\blender.exe" --background ^
     --python "<this skill>\scripts\glb_to_fbx.py" -- --src "<asset.glb>" --dst "<asset.fbx>"
   ```
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

---

## Troubleshooting
- **Hunyuan server down / not persisting**: expected across sessions — relaunch `launch_server.bat`.
- **CUDA OOM during 3D texture**: another generation is running (Fooocus?) — serialize them; or drop
  Hunyuan to `--profile 5` (already default in `launch_server.bat`).
- **Import rejects .glb**: convert to FBX first (Stage 3 step 1).
- **hf.exe fails / model download WinError 1314**: use the Python `huggingface_hub` API with
  `HF_HUB_DISABLE_SYMLINKS=1` (see `hunyuan3d-deployment` memory) — but for generation you only need
  the server up, not re-downloads.
- **Blender import shows one mesh named `*.ply`**: normal (Hunyuan meshes carry no node name); the FBX
  still exports fine.
