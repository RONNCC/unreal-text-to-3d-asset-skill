# -*- coding: utf-8 -*-
"""Text -> image via the Fooocus-API server (REST). Requires the server running on :8888.

  C:\\AI\\Fooocus-API\\python_embeded\\python.exe -s fooocus_gen.py ^
    --prompt "a green steam locomotive, single centered object, plain white background" ^
    --out C:\\path\\out.png

IMPORTANT: stop the Hunyuan3D server (port 8080) before generating — both loaded at once
exhausts the 8 GB GPU + 32 GB RAM and swaps to disk (~10x slower). Run stages sequentially.
"""
import argparse, os, sys, time, requests


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--negative", default="blurry, multiple objects, cluttered background, text, watermark")
    ap.add_argument("--out", required=True, help="output PNG path")
    ap.add_argument("--url", default="http://127.0.0.1:8888")
    ap.add_argument("--performance", default="Speed",
                    help="Speed (30 steps) | Quality (60) | 'Extreme Speed' (LCM, needs its LoRA) | Lightning")
    ap.add_argument("--ratio", default="1152*896", help="a Fooocus aspect ratio, e.g. 1152*896, 1024*1024")
    ap.add_argument("--seed", type=int, default=-1, help="-1 = random")
    args = ap.parse_args()

    payload = {
        "prompt": args.prompt,
        "negative_prompt": args.negative,
        "performance_selection": args.performance,
        "aspect_ratios_selection": args.ratio,
        "image_number": 1,
        "image_seed": args.seed,
        "require_base64": False,
        "async_process": False,   # block until the image is ready
    }
    print(f"[fooocus] generating: {args.prompt!r}", flush=True)
    t0 = time.time()
    r = requests.post(args.url + "/v1/generation/text-to-image", json=payload, timeout=1800)
    r.raise_for_status()
    data = r.json()
    img = data[0] if isinstance(data, list) and data else data
    if not isinstance(img, dict) or img.get("finish_reason") != "SUCCESS":
        sys.exit(f"[fooocus] generation failed: {img}")
    u = img["url"]
    if u.startswith("/"):
        u = args.url + u
    png = requests.get(u, timeout=120).content
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "wb") as f:
        f.write(png)
    print(f"[fooocus] done in {time.time()-t0:.1f}s -> {args.out} ({len(png)//1024} KB) seed={img.get('seed')}", flush=True)


if __name__ == "__main__":
    main()
