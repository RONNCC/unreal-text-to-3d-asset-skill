#!/usr/bin/env python3
"""Build and render a small, cute isometric Nessie amusement-park diorama.

This is intentionally procedural: no external models, fonts, or textures are
required. It creates an editable .blend, an Unreal-ready GLB, and a square PNG
preview in this directory.

Run from the repository root with Blender's Python (bpy):
    python examples/nessie_amusement_park/build_nessie_park.py
"""
from __future__ import annotations

import math
import os
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
TAU = math.tau

# A compact pastel palette: readable from an isometric camera and deliberately
# shared between objects to avoid material bloat in the exported GLB.
COLORS = {
    "grass": (0.42, 0.73, 0.45, 1),
    "grass_dark": (0.22, 0.54, 0.34, 1),
    "earth": (0.46, 0.29, 0.22, 1),
    "water": (0.20, 0.68, 0.83, 1),
    "water_light": (0.55, 0.91, 0.94, 1),
    "path": (0.96, 0.78, 0.57, 1),
    "nessie": (0.21, 0.66, 0.47, 1),
    "nessie_light": (0.52, 0.88, 0.60, 1),
    "pink": (1.0, 0.49, 0.62, 1),
    "coral": (0.95, 0.36, 0.30, 1),
    "yellow": (1.0, 0.79, 0.25, 1),
    "cream": (1.0, 0.94, 0.75, 1),
    "purple": (0.55, 0.39, 0.79, 1),
    "blue": (0.27, 0.56, 0.91, 1),
    "wood": (0.52, 0.30, 0.17, 1),
    "white": (0.98, 0.98, 0.96, 1),
    "black": (0.035, 0.045, 0.055, 1),
    "skin": (0.75, 0.43, 0.28, 1),
}
MATS = {}


def material(name, color, roughness=0.78, metallic=0.0):
    if name in MATS:
        return MATS[name]
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = color
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    MATS[name] = mat
    return mat


def apply_mat(obj, mat_name):
    obj.data.materials.append(material(mat_name, COLORS[mat_name]))
    return obj


def smooth(obj):
    if obj.type == "MESH":
        for polygon in obj.data.polygons:
            polygon.use_smooth = True
    return obj


def cube(name, loc, scale, mat_name, bevel=0.0, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(location=loc, rotation=rot)
    obj = bpy.context.object
    obj.name = name
    obj.scale = tuple(v / 2 for v in scale)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    apply_mat(obj, mat_name)
    if bevel:
        mod = obj.modifiers.new("Soft corners", "BEVEL")
        mod.width = bevel
        mod.segments = 2
    return obj


def sphere(name, loc, scale, mat_name, segments=24, rings=12):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    apply_mat(obj, mat_name)
    return smooth(obj)


def cyl(name, loc, radius, depth, mat_name, vertices=24, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc, rotation=rot)
    obj = bpy.context.object
    obj.name = name
    apply_mat(obj, mat_name)
    return obj


def cone(name, loc, r1, r2, depth, mat_name, vertices=20, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cone_add(vertices=vertices, radius1=r1, radius2=r2, depth=depth, location=loc, rotation=rot)
    obj = bpy.context.object
    obj.name = name
    apply_mat(obj, mat_name)
    return obj


def torus(name, loc, major, minor, mat_name, rot=(0, 0, 0), major_segments=32, minor_segments=8):
    bpy.ops.mesh.primitive_torus_add(
        major_radius=major, minor_radius=minor, major_segments=major_segments,
        minor_segments=minor_segments, location=loc, rotation=rot,
    )
    obj = bpy.context.object
    obj.name = name
    apply_mat(obj, mat_name)
    return smooth(obj)


def curve(name, points, bevel, mat_name, cyclic=False):
    data = bpy.data.curves.new(name, "CURVE")
    data.dimensions = "3D"
    data.bevel_depth = bevel
    data.bevel_resolution = 2
    spline = data.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    for bp, point in zip(spline.bezier_points, points):
        bp.co = point
        bp.handle_left_type = "AUTO"
        bp.handle_right_type = "AUTO"
    spline.use_cyclic_u = cyclic
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    apply_mat(obj, mat_name)
    return obj


def collection(name):
    coll = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(coll)
    return coll


def move_to_collection(obj, coll):
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    coll.objects.link(obj)


def put_last_in(coll, count_before):
    for obj in list(bpy.context.scene.objects)[count_before:]:
        move_to_collection(obj, coll)


def add_park_base():
    coll = collection("00_Park_Base")
    before = len(bpy.context.scene.objects)
    cube("Floating_island_soil", (0, 0, -0.55), (13.5, 11.5, 1.1), "earth", 0.65)
    cube("Rounded_grass_top", (0, 0, 0.04), (13.2, 11.2, 0.34), "grass", 0.75)
    # Pond sits centrally and reads as the Loch at a glance.
    sphere("Loch_water", (0.0, 0.5, 0.25), (3.25, 2.05, 0.16), "water", 40, 16)
    # A clean looping path links entrance, rides and snack area.
    loop = [(-0.1, -4.9, 0.28), (-3.7, -3.6, 0.28), (-5.0, -0.6, 0.28),
            (-4.2, 3.35, 0.28), (-0.4, 4.45, 0.28), (4.3, 3.4, 0.28),
            (5.05, 0.0, 0.28), (3.7, -3.45, 0.28), (-0.1, -4.9, 0.28)]
    curve("Main_loop_path", loop, 0.62, "path", True)
    # Short spurs make all attractions visibly accessible.
    for i, pts in enumerate([
        [(-3.8, -3.3, .29), (-2.7, -2.7, .29)],
        [(-4.3, 2.8, .29), (-3.4, 2.2, .29)],
        [(4.3, 2.8, .29), (3.25, 2.2, .29)],
        [(3.6, -3.0, .29), (2.5, -2.4, .29)],
    ]):
        curve(f"Path_spur_{i+1}", pts, 0.45, "path")
    put_last_in(coll, before)


def add_nessie():
    coll = collection("01_Nessie_Loch_Coaster")
    before = len(bpy.context.scene.objects)
    # Three smiling humps double as a tiny ride train around the Loch.
    for i, (x, y, sx) in enumerate([(-1.85, .75, 1.0), (-.45, 1.45, .9), (1.05, .8, .82)]):
        sphere(f"Nessie_hump_{i+1}", (x, y, .75), (sx, .63, .82), "nessie")
        cone(f"Hump_fin_{i+1}", (x, y, 1.55), .22, .02, .55, "nessie_light", 12)
    # Long neck, head, snout and friendly face.
    neck_points = [(1.65, .5, .58), (2.15, .55, 1.3), (2.0, .45, 2.2), (2.3, .25, 2.85)]
    curve("Nessie_neck", neck_points, .43, "nessie")
    sphere("Nessie_head", (2.33, .17, 3.0), (.72, .58, .56), "nessie")
    sphere("Nessie_muzzle", (2.55, -.32, 2.88), (.48, .35, .30), "nessie_light")
    # Eyes face the camera at -Y.
    for x in (2.04, 2.52):
        sphere("Nessie_eye_white", (x, -.36, 3.23), (.14, .09, .17), "white", 16, 8)
        sphere("Nessie_eye_pupil", (x, -.435, 3.22), (.058, .04, .075), "black", 12, 6)
    curve("Nessie_smile", [(2.30, -.64, 2.86), (2.48, -.69, 2.77), (2.67, -.62, 2.84)], .027, "black")
    # Tiny coaster boats hugging two humps communicate that Nessie is a ride.
    for i, (x, y, color) in enumerate([(-1.8, -.05, "pink"), (-.5, .72, "yellow"), (.85, .16, "purple")]):
        cube(f"Coaster_boat_{i+1}", (x, y, .72), (.72, .45, .25), color, .12)
        sphere(f"Rider_head_{i+1}", (x, y-.04, 1.05), (.14, .14, .14), "skin", 12, 6)
    # White water rings sell the emerging-monster silhouette.
    for i, (x, y, r) in enumerate([(-1.85,.75,1.0),(-.45,1.45,.85),(1.05,.8,.78),(1.7,.5,.65)]):
        torus(f"Water_ripple_{i+1}", (x, y, .43), r, .045, "water_light")
    put_last_in(coll, before)


def add_ferris_wheel():
    coll = collection("02_Loch_View_Wheel")
    before = len(bpy.context.scene.objects)
    cx, cy, cz = -4.25, 2.65, 2.2
    # Wheel plane is X/Z so it reads clearly from the camera.
    torus("View_wheel_rim", (cx, cy, cz), 1.48, .095, "cream", rot=(math.pi/2, 0, 0), major_segments=32)
    cyl("Wheel_axle", (cx, cy, cz), .18, .85, "yellow", rot=(math.pi/2, 0, 0))
    for angle in [i*TAU/8 for i in range(8)]:
        x, z = cx + 1.48*math.cos(angle), cz + 1.48*math.sin(angle)
        curve("Wheel_spoke", [(cx,cy,cz), (x,cy,z)], .035, "white")
        # Cute bucket gondolas, always upright.
        cube("Gondola", (x, cy-.05, z-.12), (.48,.5,.35), "pink" if int(angle*8/TAU)%2 else "blue", .10)
        sphere("Gondola_bobble", (x, cy-.05, z+.12), (.08,.08,.08), "yellow", 12, 6)
    # A-frame supports.
    for y in (cy-.34, cy+.34):
        curve("Wheel_support", [(cx-1.2,y,.38),(cx,y,cz)], .09, "purple")
        curve("Wheel_support", [(cx+1.2,y,.38),(cx,y,cz)], .09, "purple")
    put_last_in(coll, before)


def add_lily_spinner():
    coll = collection("03_Lily_Cup_Spinner")
    before = len(bpy.context.scene.objects)
    cx, cy = -3.25, -2.65
    cyl("Lily_spinner_platform", (cx,cy,.45), 1.38, .28, "water_light", 32)
    cyl("Spinner_hub", (cx,cy,.75), .26, .65, "yellow", 20)
    for i, color in enumerate(("pink", "purple", "blue")):
        a = TAU*i/3 + .25
        x,y = cx+.82*math.cos(a), cy+.82*math.sin(a)
        cyl("Lily_pad", (x,y,.64), .48, .12, "grass_dark", 20)
        # Cup = low round bowl plus a cream rim.
        cone("Lily_cup", (x,y,.86), .34, .26, .38, color, 20)
        torus("Cup_rim", (x,y,1.05), .29, .045, "cream")
    put_last_in(coll, before)


def add_carousel():
    coll = collection("04_Baby_Nessie_Carousel")
    before = len(bpy.context.scene.objects)
    cx, cy = 3.75, 2.25
    cyl("Carousel_deck", (cx,cy,.48), 1.35, .26, "cream", 32)
    cyl("Carousel_pole", (cx,cy,1.5), .12, 2.2, "yellow", 16)
    cone("Carousel_canopy", (cx,cy,2.48), 1.55, .28, .72, "pink", 32)
    sphere("Canopy_topper", (cx,cy,2.92), (.20,.20,.20), "yellow", 16, 8)
    for i, color in enumerate(("blue", "purple", "coral", "yellow")):
        a = TAU*i/4 + .45
        x,y = cx+.83*math.cos(a), cy+.83*math.sin(a)
        cyl("Ride_pole", (x,y,1.5), .035, 1.65, "white", 10)
        # Baby-Nessie ride animal: bean body, head and little fin.
        sphere("Baby_Nessie_body", (x,y,.98), (.43,.23,.25), color, 16, 8)
        sphere("Baby_Nessie_head", (x+.28,y-.08,1.19), (.22,.19,.22), color, 16, 8)
        sphere("Baby_Nessie_eye", (x+.35,y-.24,1.24), (.04,.025,.045), "black", 10, 5)
    put_last_in(coll, before)


def add_kiosk_and_snacks():
    coll = collection("05_Kiosk_and_Snacks")
    before = len(bpy.context.scene.objects)
    # Tiny turreted ticket kiosk at the loop's lower right.
    cube("Ticket_kiosk", (3.25,-2.65,1.05), (1.65,1.35,1.65), "cream", .14)
    cube("Ticket_window", (3.25,-3.345,1.15), (.9,.05,.65), "water")
    cone("Kiosk_roof", (3.25,-2.65,2.20), 1.22, .12, .85, "purple", 4, rot=(0,0,math.pi/4))
    sphere("Roof_flag_ball", (3.25,-2.65,2.70), (.12,.12,.12), "yellow", 12, 6)
    # Snack cart with striped awning and candy-floss bubble.
    cube("Snack_cart", (4.95,-1.55,.82), (1.15,.72,1.05), "coral", .10)
    for i in range(5):
        cube("Awning_stripe", (4.55+i*.2,-1.55,1.52), (.2,.92,.16), "white" if i%2 else "yellow", .04)
    for x in (4.55,5.35):
        cyl("Cart_wheel", (x,-1.92,.39), .18, .10, "black", 14, rot=(math.pi/2,0,0))
    sphere("Candy_floss", (5.48,-1.80,1.62), (.23,.23,.29), "pink", 16, 8)
    curve("Candy_floss_stick", [(5.48,-1.80,1.1),(5.48,-1.80,1.48)], .025, "wood")
    put_last_in(coll, before)


def add_entrance_people_and_details():
    coll = collection("06_Entrance_Guests_and_Details")
    before = len(bpy.context.scene.objects)
    # Entrance arch, with a readable mesh sign converted from Blender text.
    for x in (-1.25,1.25):
        cyl("Entrance_post", (x,-4.85,1.0), .14, 1.5, "purple", 16)
        sphere("Post_bobble", (x,-4.85,1.78), (.22,.22,.22), "yellow", 16, 8)
    curve("Entrance_arch", [(-1.25,-4.85,1.65),(0,-4.85,2.55),(1.25,-4.85,1.65)], .13, "pink")
    bpy.ops.object.text_add(location=(-.82,-5.02,1.98), rotation=(math.pi/2,0,0))
    sign = bpy.context.object
    sign.name = "NESSIE_sign"
    sign.data.body = "NESSIE"
    sign.data.align_x = "LEFT"
    sign.data.size = .42
    sign.data.extrude = .025
    apply_mat(sign, "cream")
    bpy.context.view_layer.objects.active = sign
    sign.select_set(True)
    bpy.ops.object.convert(target="MESH")
    # One tiny guest walking from entrance to rides.
    sphere("Guest_head", (-.55,-3.95,1.18), (.18,.18,.20), "skin", 16, 8)
    cone("Guest_body", (-.55,-3.95,.79), .28, .18, .60, "blue", 16)
    for x in (-.67,-.43):
        curve("Guest_leg", [(x,-3.95,.52),(x+(.08 if x<-.5 else -.08),-3.88,.27)], .055, "black")
    cone("Guest_hat", (-.55,-3.95,1.41), .27, .05, .24, "yellow", 16)
    # Benches, flowers, shrubs and lamps give human scale without clutter.
    for x,y,r in [(-5.35,-3.9,0),(5.2,3.8,math.pi),(-5.4,.0,math.pi/2)]:
        cube("Bench_seat", (x,y,.58), (1.15,.36,.16), "wood", .05, rot=(0,0,r))
        cube("Bench_back", (x,y+.13*math.cos(r),.90), (1.15,.12,.55), "wood", .04, rot=(0,0,r))
    for x,y in [(-5.6,4.3),(5.5,4.0),(-5.5,-1.7),(5.45,.0),(1.8,-4.35)]:
        sphere("Park_shrub", (x,y,.57), (.46,.46,.48), "grass_dark", 16, 8)
        for a in (0,2.1,4.2):
            sphere("Flower", (x+.28*math.cos(a),y+.28*math.sin(a),.91), (.09,.09,.09), "pink" if a<3 else "yellow", 10, 5)
    for x,y in [(-2.1,-4.3),(2.0,4.2)]:
        cyl("Lamp_post", (x,y,1.05), .055, 1.45, "purple", 10)
        sphere("Lamp_globe", (x,y,1.82), (.20,.20,.25), "cream", 16, 8)
    put_last_in(coll, before)


def setup_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    # Cycles CPU renders headlessly without a GL/EGL display, including in CI.
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 48
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 768
    scene.render.resolution_y = 768
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    scene.render.filepath = str(HERE / "nessie_amusement_park.png")
    # Contact shadows + ambient world produce the soft toy-diorama look.
    world = bpy.data.worlds.new("Pastel_sky")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.76,0.89,0.94,1)
    world.node_tree.nodes["Background"].inputs[1].default_value = .75
    scene.world = world
    bpy.ops.object.light_add(type="AREA", location=(-4,-6,13))
    key = bpy.context.object
    key.name = "Softbox"
    key.data.energy = 1350
    key.data.shape = "DISK"
    key.data.size = 8
    bpy.ops.object.light_add(type="AREA", location=(8,4,8))
    fill = bpy.context.object
    fill.name = "Fill"
    fill.data.energy = 650
    fill.data.size = 7
    # Orthographic 3/4 camera; all attractions are composed for this view.
    bpy.ops.object.camera_add(location=(13,-17,14))
    cam = bpy.context.object
    cam.name = "Isometric_Camera"
    direction = Vector((0,0,.75)) - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 18.2
    scene.camera = cam
    scene.view_settings.look = "AgX - Medium High Contrast"


def export_all():
    # Mesh-evaluate bevel modifiers and convert curves/text so engines receive
    # plain renderable meshes rather than Blender-only procedural objects.
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE / "nessie_amusement_park.blend"))
    bpy.ops.object.select_all(action="DESELECT")
    exportables = [o for o in bpy.context.scene.objects if o.type in {"MESH","CURVE","FONT"}]
    for obj in exportables:
        obj.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=str(HERE / "nessie_amusement_park.glb"),
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_animations=False,
        export_cameras=False,
        export_lights=False,
    )
    bpy.context.scene.render.filepath = str(HERE / "nessie_amusement_park.png")
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    setup_scene()
    add_park_base()
    add_nessie()
    add_ferris_wheel()
    add_lily_spinner()
    add_carousel()
    add_kiosk_and_snacks()
    add_entrance_people_and_details()
    export_all()
    print("Created:")
    for filename in ("nessie_amusement_park.blend", "nessie_amusement_park.glb", "nessie_amusement_park.png"):
        path = HERE / filename
        print(f"  {path} ({path.stat().st_size/1024/1024:.2f} MiB)")
