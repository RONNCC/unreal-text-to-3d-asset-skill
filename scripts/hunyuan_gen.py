# -*- coding: utf-8 -*-
"""Photo -> 3D GLB via a running Hunyuan3D-2 server (default localhost:8080).

  python3 scripts/hunyuan_gen.py --image X.png --name Foo [--mode textured|shape] \\
      [--server auto|gradio|api]

Two DIFFERENT official servers exist upstream, and they do not speak the same
protocol:

  --server gradio   Hunyuan3D-2's gradio_app.py (the web UI). Talked to with
                    gradio_client (fn /generation_all, /shape_generation).
                    This is what the upstream Windows skill used.
  --server api      Hunyuan3D-2's api_server.py (FastAPI). Plain HTTP:
                    POST {url}/generate with a JSON body (base64 image) and the
                    GLB comes back as the raw response body. This is what the
                    repo's Dockerfile.hunyuan launches. Texture only works if
                    the server was started with --enable_tex.
  --server auto     (default) GET /openapi.json: FastAPI answers it, the
                    gradio UI does not -> picks the right protocol for you.

The server URL comes from --url, defaulting to the HUNYUAN_URL environment
variable (or http://localhost:8080). On Apple Silicon the GPU path is CUDA-only
upstream, so expect MPS/CPU performance locally or point HUNYUAN_URL at a
remote NVIDIA box. The server must be up first.
"""
import argparse, base64, os, shutil, sys, time

import requests


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True, help="path to input image")
    ap.add_argument("--out", default=os.environ.get("HUNYUAN_OUT", "output"),
                    help="output FOLDER for GLBs (files land at <out>/<name>_textured.glb)")
    ap.add_argument("--name", default=None, help="basename for output (defaults to image name)")
    ap.add_argument("--mode", choices=["textured", "shape"], default="textured")
    ap.add_argument("--server", choices=["auto", "gradio", "api"], default="auto",
                    help="server protocol: gradio_app.py | api_server.py | auto-detect")
    ap.add_argument("--url", default=os.environ.get("HUNYUAN_URL", "http://localhost:8080"))
    ap.add_argument("--seed", type=int, default=1234)
    ap.add_argument("--steps", type=int, default=5)      # turbo default
    ap.add_argument("--octree", type=int, default=256)   # mesh resolution
    ap.add_argument("--no-rembg", action="store_true",
                    help="skip background removal (gradio server only; api_server always rembgs)")
    args = ap.parse_args()
    if not os.path.isfile(args.image):
        sys.exit(f"[hunyuan] input image not found: {args.image}")
    os.makedirs(args.out, exist_ok=True)
    return args


def detect_server(url):
    """Return 'api' if {url} looks like Hunyuan3D-2's FastAPI api_server.py, else 'gradio'."""
    try:
        r = requests.get(url.rstrip("/") + "/openapi.json", timeout=10)
        if r.status_code == 200:
            paths = r.json().get("paths", {})
            if "/generate" in paths:
                return "api"
    except requests.RequestException:
        pass
    return "gradio"


def save_result(content, args, tag):
    dst = os.path.join(args.out, f"{args.name}_{tag}.glb")
    with open(dst, "wb") as f:
        f.write(content)
    # sanity: a GLB starts with the magic bytes 'glTF'
    ok = content[:4] == b"glTF"
    print(f"[hunyuan]   -> {dst}  ({len(content)/1024:.0f} KB){'' if ok else '  WARNING: not a GLB!'}", flush=True)
    if not ok:
        sys.exit(f"[hunyuan] ERROR: server did not return a GLB (first bytes: {content[:16]!r})")
    return dst


def run_via_api(args):
    """api_server.py contract: POST /generate {image: base64, ...} -> GLB bytes."""
    url = args.url.rstrip("/") + "/generate"
    with open(args.image, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode("ascii")
    payload = {
        "image": img_b64,
        "seed": args.seed,
        "octree_resolution": args.octree,
        "num_inference_steps": args.steps,
        "guidance_scale": 5.0,
        "texture": args.mode == "textured",
        "type": "glb",
    }
    print(f"[hunyuan] POST {url} (api_server.py, texture={payload['texture']}) ...", flush=True)
    t0 = time.time()
    try:
        r = requests.post(url, json=payload, timeout=3600)
    except requests.ConnectionError:
        sys.exit(f"[hunyuan] ERROR: cannot connect to {args.url} — is the server running? "
                 f"(api_server.py; start it or set HUNYUAN_URL)")
    dt = time.time() - t0
    ctype = r.headers.get("content-type", "")
    if r.status_code != 200 or "json" in ctype:
        try:
            detail = r.json()
        except ValueError:
            detail = r.text[:500]
        sys.exit(f"[hunyuan] ERROR: server returned HTTP {r.status_code}: {detail!r}\n"
                 f"         (textured mode needs the server started with --enable_tex)")
    print(f"[hunyuan] done in {dt:.1f}s (api mode)", flush=True)
    save_result(r.content, args, "textured" if args.mode == "textured" else "white")


def run_via_gradio(args):
    """gradio_app.py contract: gradio_client fn /generation_all (+/shape_generation)."""
    try:
        from gradio_client import Client, handle_file
    except ImportError:
        sys.exit("[hunyuan] ERROR: --server gradio needs gradio_client (pip install gradio_client).\n"
                 "         If the server is api_server.py / the Dockerfile.hunyuan container,\n"
                 "         re-run with --server api (needs only 'requests').")
    api = "/generation_all" if args.mode == "textured" else "/shape_generation"
    print(f"[hunyuan] connecting to {args.url} (gradio_app.py) ...", flush=True)
    try:
        c = Client(args.url, verbose=False)
    except Exception as e:  # gradio_client raises broad Exception types on connect
        sys.exit(f"[hunyuan] ERROR: cannot connect to {args.url} — is gradio_app.py running? ({e})")
    print(f"[hunyuan] {args.mode} generation from {args.image} via {api} ...", flush=True)
    t0 = time.time()
    res = c.predict(
        None,                     # caption
        handle_file(args.image),  # image
        None, None, None, None,   # mv front/back/left/right
        args.steps, 5.0, args.seed, args.octree,
        (not args.no_rembg),      # check_box_rembg
        8000, True,               # num_chunks, randomize_seed
        api_name=api,
    )
    dt = time.time() - t0

    items = res if isinstance(res, (list, tuple)) else [res]
    saved = []
    for item in items:
        p = item.get("value") if isinstance(item, dict) else item
        if isinstance(p, str) and os.path.isfile(p) and p.lower().endswith((".glb", ".obj")):
            base = os.path.basename(p)
            tag = "textured" if "textured" in base else ("white" if "white" in base else "mesh")
            dst = os.path.join(args.out, f"{args.name}_{tag}{os.path.splitext(p)[1]}")
            shutil.copy(p, dst)
            saved.append((dst, os.path.getsize(dst)))

    print(f"[hunyuan] done in {dt:.1f}s (gradio mode)", flush=True)
    for dst, size in saved:
        print(f"[hunyuan]   -> {dst}  ({size/1024:.0f} KB)", flush=True)
    if not saved:
        sys.exit("[hunyuan] ERROR: no mesh file returned (raw result: %r)" % (res,))


def main():
    args = parse_args()
    args.name = args.name or os.path.splitext(os.path.basename(args.image))[0]
    server = args.server
    if server == "auto":
        server = detect_server(args.url)
        print(f"[hunyuan] auto-detected server type: {server}", flush=True)
    if server == "api":
        run_via_api(args)
    else:
        run_via_gradio(args)


if __name__ == "__main__":
    main()
