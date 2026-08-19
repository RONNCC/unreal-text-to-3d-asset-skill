# Nessie's Lagoon — cute isometric amusement park

This is the design artifact for the `nessie_park` example. It follows the five
steps from the request: **(1) idea → (2) self-audit → (3) ride list & layout &
connectivity → (4) keep it small/fun/cute + a person → (5) audited final plan.**
The actual assets are generated procedurally by `build_park.py` (Blender/bpy,
CPU-only — no GPU/AI required) and rendered with Cycles.

> **Note on the reference photo:** the attached reference image did not come
> through to this build session, so this follows the written brief — a *fun,
> cute, isometric* Nessie amusement park that is *small* and has *a person
> walking around*. If the reference shows specific ride colors/positions, send
> it again and I'll match them; the scene is data-driven so changes are quick.

---

## 1. Idea

**"Nessie's Lagoon"** — a tiny floating-island amusement park themed around a
friendly sea monster. A chubby three-humped Nessie swims in a turquoise loch at
the center of the island, and three small rides + a handful of stalls ring it.
A cream-colored path loops from the entrance arch around the loch, connecting
every ride and stall, so a little visitor can actually walk between them.

**Visual language** (the "cute isometric" target):
- Chibi / toy proportions: everything short, rounded, puffy.
- Soft pastel palette, matte materials, gentle even lighting, soft shadows.
- Classic isometric camera (30° down, viewport rotated 45°), orthographic.
- Floating rounded island over a faint sky/void so the whole diorama reads as
  one self-contained toy — no ugly ground plane running off to infinity.

## 2. Self-audit of the idea

| Concern | Resolution |
|---|---|
| "Amusement park" can sprawl and look busy/messy | Keep it to **3 rides + 2 stalls + decor**. Single looping path. One mascot. Tight footprint (~14 units). |
| Nessie could look scary (monster!) | Make it **chibi**: big head, three soft humps, tiny tail, round eyes, blush, a smile, a little water spout. Pastel teal. |
| Rides could read as random blobs in isometric | Each ride is **silhouette-distinct**: Ferris wheel (big circle), carousel (striped tent), coaster (elevated loop). |
| Things need to "connect" (step 3) | A continuous cream **path** runs entrance → Nessie pond → each ride/stall and back. Benches + lamps line it. |
| A person "walking around" (step 4) | One **low-poly chibi visitor** mid-stride on the path, facing toward Nessie. |
| Procedural boxes look "ugly/hard" — the previous failure mode | Add **bevel + subdivision-style rounding** to every hard edge, matte pastel colors, soft sun + ambient occlusion. |
| Performance (no GPU, 2 CPU / 3.8 GB) | Low-poly (~tens of verts per prop), Cycles CPU, 32–64 samples, modest 1400px frame. Bakes in seconds. |

## 3. Rides, stalls & how they connect

**Rides (3):**
1. **Nessie Ferris wheel** (back-left) — cream frame, 8 pastel gondolas, turns.
   The largest silhouette; anchors the skyline.
2. **Carousel** (back-right) — red-and-cream striped cone tent, pastel horses on
   gold poles, scalloped base.
3. **Nessie-coaster** (front/left loop) — a short elevated oval track on cream
   supports with a little 3-car train (one car has a fin so it reads as a
   monster train). The track loops behind the pond.

**Stalls (2):**
4. **Ice-cream / snack stand** (right) — pastel booth with a striped awning and
   a giant soft-serve on the roof.
5. **Ticket booth + entrance arch** (front-center) — two flags, a "Nessie's
   Lagoon" arch (sign is an arched mesh; no text baked in — see audit).

**Centerpiece & decor:**
- **Nessie** swimming in the pond (heart of the park), three humps + head + tail.
- Turquoise **loch** with a sandy rim; little water spout from Nessie's head.
- Rounded **trees** (lollipop style), bushes, and flowers scattered on the grass.
- Two puffy **clouds** floating above.
- Benches and **lampposts** along the path.
- One **visitor** walking on the path.

**Layout (top-down, isometric orientation):**
```
                     Ferris wheel        Carousel
                          \       |       /
                           \  path loop  /
                            \           /
            coaster ======  POND+NESSIE  =====  (back of loop)
                            /          \
                       path            path
                          \            /
                      ice-cream    (open lawn)
                            \        /
                          entrance arch + ticket booth
                             (visitor here)
```
The cream path is a single closed rounded-rectangle loop around the pond. Every
ride and stall sits just off the loop with a short spur path to it, so the whole
park is walkable and nothing floats disconnected.

## 4. Keeping it small, fun & cute

- **Scale:** island ≈ 14 units across; Ferris wheel is the tallest thing (~8).
- **Cuteness levers:** rounded bevels on everything; pastel palette; chibi
  Nessie with eyes + blush + smile; a tiny train; a waving visitor; puffy clouds.
- **The person:** a single chibi visitor (round head, cap, little backpack)
  mid-walk on the path by the entrance, looking at Nessie.
- **One focal point:** Nessie in the pond. Everything else frames it.

## 5. Final plan (what `build_park.py` produces)

1. Reset to empty scene; set pastel **world** + soft sun + isometric **camera**.
2. Build the **floating island** (grass slab + dirt underbelly) and **pond**.
3. Lay the **path** loop and spur tiles (cream, rounded).
4. Build each **ride** (Ferris wheel, carousel, coaster) and **stalls**.
5. Place the **Nessie** centerpiece in the pond (head + 3 humps + tail + spout).
6. Scatter **trees, bushes, flowers, benches, lamps, clouds**.
7. Place the **visitor** on the path.
8. Render `output/nessie_park.png` (Cycles CPU, isometric).
9. Export the whole diorama to `output/nessie_park.glb`.

**Files:**
- `build_park.py` — the procedural scene builder.
- `render.sh` — env wrapper so bpy finds its stub libs + bundled libs.
- `output/nessie_park.png` — the finished isometric render.
- `output/nessie_park.glb` — the diorama as a 3D asset.
