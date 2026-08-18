# Nessie's Little Loch — concept, layout, and audit

## 1. Idea

**Nessie's Little Loch** is a pocket-sized, toy-like amusement park built on a
floating square of the Scottish Highlands. The park mascot is not a statue:
Nessie rises from the central loch and forms the main family coaster. Everything
uses rounded low-poly shapes, a pastel palette, and an orthographic isometric
composition so it reads like a cute tabletop model.

Design pillars:

1. **Nessie first** — the face, neck, humps, ripples, and three little ride boats
   occupy the visual center.
2. **Small but complete** — four rides plus entrance, ticketing, food, seating,
   lighting, landscaping, and one guest.
3. **One-glance navigation** — a cream loop path connects every attraction.
4. **Toy-diorama style** — no realism, grunge, signage clutter, or sharp forms.

## 2. Idea audit (before building)

| Question | Risk found | Decision |
|---|---|---|
| Is “Nessie park” visible instantly? | A generic park with a Nessie statue would be weak. | Make Nessie the central water coaster and tallest character. |
| Can it stay small? | Too many rides would make the isometric image noisy. | Cap it at four recognizable attractions and one food cart. |
| Does every ride have access? | Isolated props can look like a model collection rather than a park. | Use one continuous outer loop with four short attraction spurs. |
| Will the silhouette read? | Ferris wheel, carousel and Nessie neck could overlap. | Put tall rides at opposite rear corners and Nessie just right of center. |
| Is it cute rather than spooky? | Dark water and a realistic monster would change the tone. | Use mint Nessie, giant eyes, a smile, pale-blue water and candy colors. |
| Is it useful as a 3D example? | A beauty image alone is not reusable. | Ship editable `.blend`, GLB, FBX, source generator and preview. |

## 3. Attractions and layout

Approximate plan view (the isometric camera looks from the south-east):

```text
              NORTH / back

      Loch View Wheel        Baby Nessie Carousel
             [A]                     [B]
                 +---- cream path ----+
              .-------------------------.
             /      central LOCH         \
            |  humps + boats    NESSIE   |
            |                             |
 Lily Cup   [C]                         snack cart
 Spinner      \                         /
               +---- ticket kiosk [D]--+
                   guest   ENTRANCE

              SOUTH / front
```

### Attraction set

- **Central Nessie Loch Coaster** — three green humps become the ride route;
  pink, yellow, and purple boats carry tiny riders between white-water ripples.
- **Loch View Wheel** — eight alternating blue/pink gondolas on a cream wheel,
  placed rear-left for a clean silhouette.
- **Lily Cup Spinner** — three colorful teacups on lily pads, placed front-left
  and kept low so it does not hide Nessie.
- **Baby Nessie Carousel** — four tiny monster mounts under a pink canopy,
  placed rear-right as a visual counterweight to the wheel.
- **Ticket kiosk and snack cart** — a turret-roof booth and striped cart make
  the park feel operational without adding another full building.

### Connections and guest flow

The entrance is centered on the south edge. A guest passes under the NESSIE
arch and immediately meets the loop path. Clockwise, it reaches the lily
spinner, view wheel, carousel, snack cart and ticket kiosk before returning to
the entrance. Four short path spurs make the attraction connections explicit.
Benches sit on quiet outer edges rather than blocking ride approaches.

## 4. Small/cute scope controls

- Footprint: about **13.5 × 11.5 Blender metres**, intentionally a compact
  “one-screen” park.
- Palette: 18 shared flat pastel materials; no external texture dependencies.
- Geometry: rounded primitive forms and moderate segment counts.
- Population: one clearly visible walking guest plus three tiny coaster riders.
- Dressing: three benches, five flowering shrubs and two lamps — enough scale
  cues without visual clutter.

## 5. Post-build visual and technical audit

### What works

- **Hierarchy:** Nessie is central, largest, and the only figure with a detailed
  face; the wheel and canopy are secondary anchors.
- **Readability:** all four attractions remain visible from the final camera.
- **Connectivity:** the continuous cream path reads immediately and every ride
  has a spur or adjacent stopping point.
- **Tone:** soft corners, pale ground, candy accents and oversized facial
  features consistently support the requested cute style.
- **Human scale:** the entrance guest, riders, benches and kiosk make the scene
  feel like a usable park rather than a monument.
- **Deliverability:** the GLB validates as glTF 2.0 and converts through the
  repository's real GLB→FBX path.

### Known trade-offs / next-pass opportunities

- It is an intentionally static diorama. In Unreal, wheel, carousel and coaster
  boats should be separated into animated Blueprints if interactive motion is
  required.
- The central loch is opaque pastel geometry, not a physically simulated water
  material. That choice preserves the toy style and portable GLB materials.
- The scene imports as many named mesh parts (useful for editing), not one
  aggressively draw-call-optimized combined mesh. Merge static dressing and
  instance repeated flowers/gondolas for a production mobile target.
- The single orthographic composition was prioritized. A ground-level player
  version would need wider paths, rails, queue gates and collision review.

**Audit result:** the compact concept succeeds as an isometric example and as a
modular blockout. No layout blockers were found. The main production follow-up
would be interaction/optimization, not a redesign.

## 6. Initial production plan

1. **Approve the visual target** using `nessie_amusement_park.png`.
2. **Import `nessie_amusement_park.fbx` into Unreal** with “Combine Meshes” off
   if individual attraction editing/animation is wanted; on for a static prop.
3. **Create attraction Blueprints** for the view wheel, carousel and coaster
   boats, keeping fixed supports in static-mesh components.
4. **Add simple collision** to the island/path/kiosk only; disable collision on
   tiny flowers, spokes and decorative ripples.
5. **Add animation:** slow wheel rotation, carousel rotation, three boat loops,
   Nessie blink, and a gentle head bob.
6. **Add ambience:** cheerful loch music, small ride bells, water splashes and
   guest footsteps.
7. **Optimize after profiling:** instance repeats, merge static dressing and
   add LODs only if the intended camera can move closer.

## Files

| File | Purpose |
|---|---|
| `nessie_amusement_park.png` | 768×768 final isometric preview |
| `nessie_amusement_park.blend` | Editable authored scene with named collections |
| `nessie_amusement_park.glb` | Portable glTF 2.0 scene |
| `nessie_amusement_park.fbx` | Unreal import asset produced by this repo's converter |
| `build_nessie_park.py` | Deterministic procedural source for all geometry/materials |
