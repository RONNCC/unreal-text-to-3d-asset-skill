# -*- coding: utf-8 -*-
"""Photo -> 3D GLB via the running Hunyuan3D-2 server (default localhost:8080).

  python3 scripts/hunyuan_gen.py --image X.png --name Foo [--mode textured|shape]

The server URL comes from --url, defaulting to the HUNYUAN_URL environment variable
(or http://localhost:8080). Works against Tencent's official api_server.py
(or its gradio_app.py) hosted locally or remotely. On Apple Silicon the GPU path is
CUDA-only upstream, so expect MPS/CPU performance locally or point HUNYUAN_URL at a
remote NVIDIA box. Server must be up first.
"""
import argparse, os, sys, time, shutil
from gradio_client import Client, handle_file


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True, help="path to input image")
    ap.add_argument("--out", default=os.environ.get("HUNYUAN_OUT", "output"), help="output folder for GLBs")
    ap.add_argument("--name", default=None, help="basename for output (defaults to image name)")
    ap.add_argument("--mode", choices=["textured", "shape"], default="textured")
    ap.add_argument("--url", default=os.environ.get("HUNYUAN_URL", "http://localhost:8080"))
    ap.add_argument("--seed", type=int, default=1234)
    ap.add_argument("--steps", type=int, default=5)      # turbo default
    ap.add_argument("--octree", type=int, default=256)   # mesh resolution
    ap.add_argument("--no-rembg", action="store_true", help="skip background removal")
    args = ap.parse_args()

    if not os.path.isfile(args.image):
        sys.exit(f"[hunyuan] input image not found: {args.image}")
    os.makedirs(args.out, exist_ok=True)
    name = args.name or os.path.splitext(os.path.basename(args.image))[0]
    api = "/generation_all" if args.mode == "textured" else "/shape_generation"

    print(f"[hunyuan] connecting to {args.url} ...", flush=True)
    c = Client(args.url, verbose=False)
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
            dst = os.path.join(args.out, f"{name}_{tag}{os.path.splitext(p)[1]}")
            shutil.copy(p, dst)
            saved.append((dst, os.path.getsize(dst)))

    print(f"[hunyuan] done in {dt:.1f}s", flush=True)
    for dst, size in saved:
        print(f"[hunyuan]   -> {dst}  ({size/1024:.0f} KB)", flush=True)
    if not saved:
        sys.exit("[hunyuan] ERROR: no mesh file returned (raw result: %r)" % (res,))


if __name__ == "__main__":
    main()
