# -*- coding: utf-8 -*-
"""Build "Nessie's Lagoon" — a cute isometric amusement-park diorama.

Procedural Blender/bpy scene, no GPU/AI required. Renders with Cycles CPU and
exports a GLB. Follow along with PLAN.md for the design / audit / layout.

Usage (see render.sh for the LD_LIBRARY_PATH wrapper):
    bpy-python build_park.py
"""
import math
import os
import random
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "output")
os.makedirs(OUT, exist_ok=True)

# ----------------------------------------------------------------------------
# Palette (soft matte pastels)
# ----------------------------------------------------------------------------
C = {
    "grass":      (0.59, 0.82, 0.49),
    "grass2":     (0.52, 0.76, 0.43),
    "dirt":       (0.55, 0.40, 0.29),
    "sand":       (0.93, 0.86, 0.62),
    "water":      (0.36, 0.78, 0.86),
    "path":       (0.97, 0.92, 0.78),
    "nessie":     (0.43, 0.74, 0.66),
    "nessie_b":   (0.36, 0.66, 0.58),
    "cream":      (0.99, 0.95, 0.84),
    "red":        (0.88, 0.36, 0.34),
    "coral":      (0.96, 0.55, 0.45),
    "gold":       (0.86, 0.72, 0.36),
    "mint":       (0.55, 0.84, 0.72),
    "sky":        (0.60, 0.82, 0.95),
    "pink":       (0.98, 0.66, 0.74),
    "lilac":      (0.74, 0.66, 0.90),
    "yellow":     (0.98, 0.85, 0.45),
    "brown":      (0.67, 0.50, 0.36),
    "bark":       (0.47, 0.33, 0.22),
    "leaf":       (0.40, 0.72, 0.40),
    "leaf2":      (0.48, 0.78, 0.46),
    "white":      (0.99, 0.99, 0.99),
    "black":      (0.08, 0.08, 0.10),
    "skin":       (1.00, 0.82, 0.67),
    "shirt":      (0.55, 0.78, 0.95),
    "cap":        (0.96, 0.45, 0.45),
    "pack":       (0.95, 0.75, 0.45),
    "denim":      (0.40, 0.50, 0.72),
    "glass":      (0.75, 0.90, 0.95),
}

random.seed(7)


# ----------------------------------------------------------------------------
# Low-level helpers
# ----------------------------------------------------------------------------
def mat(name, rgb, rough=0.65, metal=0.0, emission=None, emit_str=0.0,
        transmission=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if transmission:
        b.inputs["Transmission Weight"].default_value = transmission
    if emission:
        b.inputs["Emission Color"].default_value = (*emission, 1.0)
        b.inputs["Emission Strength"].default_value = emit_str
    return m


# Materials are built lazily after reset() (which wipes bpy.data).
M = {}


def init_materials():
    global M
    M.clear()
    for k, v in C.items():
        M[k] = mat(f"m_{k}", v)
    M["water"] = mat("m_water", C["water"], rough=0.12, transmission=0.25)
    M["lamp"] = mat("m_lamp", (1.0, 0.92, 0.7), rough=0.4,
                    emission=(1.0, 0.9, 0.6), emit_str=3.0)
    M["spout"] = mat("m_spout", (0.78, 0.94, 1.0), rough=0.1, transmission=0.6)


def _smooth(o):
    for p in o.data.polygons:
        p.use_smooth = True


def _bevel(o, width=0.1, seg=3):
    md = o.modifiers.new("bev", "BEVEL")
    md.width = width
    md.segments = seg
    md.limit_method = "NONE"
    md.harden_normals = False
    return md


def box(name, loc, size, material, bev=0.08, rot=(0, 0, 0), smooth=True):
    # A default primitive_cube_add(size=1.0) is already 1x1x1, so scale is the
    # exact desired size in each axis (no /2).
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.scale = (size[0], size[1], size[2])
    bpy.ops.object.transform_apply(scale=True)
    if bev:
        _bevel(o, bev, 3)
    o.data.materials.append(material)
    if smooth:
        _smooth(o)
    return o


def cyl(name, loc, r, depth, material, rot=(0, 0, 0), verts=24, bev=0.0,
        smooth=True):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=verts, radius=r, depth=depth, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    if bev:
        _bevel(o, bev, 2)
    o.data.materials.append(material)
    if smooth:
        _smooth(o)
    return o


def cone(name, loc, r1, r2, depth, material, rot=(0, 0, 0), verts=24,
         smooth=True):
    bpy.ops.mesh.primitive_cone_add(
        vertices=verts, radius1=r1, radius2=r2, depth=depth,
        location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.data.materials.append(material)
    if smooth:
        _smooth(o)
    return o


def sphere(name, loc, r, material, scale=(1, 1, 1), rot=(0, 0, 0), seg=24,
           ring=16):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=seg, ring_count=ring, radius=r, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.scale = scale
    bpy.ops.object.transform_apply(scale=True)
    o.data.materials.append(material)
    _smooth(o)
    return o


def torus(name, loc, major, minor, material, rot=(0, 0, 0), seg=48,
          ring=14):
    bpy.ops.mesh.primitive_torus_add(
        major_segments=seg, minor_segments=ring,
        major_radius=major, minor_radius=minor, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.data.materials.append(material)
    _smooth(o)
    return o


def cyl_between(p1, p2, r, material, name, verts=10):
    p1, p2 = Vector(p1), Vector(p2)
    mid = (p1 + p2) / 2
    length = (p2 - p1).length
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=verts, radius=r, depth=length, location=mid)
    o = bpy.context.active_object
    o.name = name
    o.rotation_euler = Vector((0, 0, 1)).rotation_difference(p2 - p1).to_euler()
    bpy.ops.object.transform_apply(rotation=True)
    o.data.materials.append(material)
    _smooth(o)
    return o


def parent(child, par):
    child.parent = par
    child.matrix_parent_inverse = par.matrix_world.inverted()


# ----------------------------------------------------------------------------
# Scene setup
# ----------------------------------------------------------------------------
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 64
    scene.cycles.use_denoising = True
    scene.cycles.caustics_reflective = False
    scene.cycles.caustics_refractive = False
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 1600
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0
    # world (soft sky) — modest strength so the pastel colors don't blow out
    world = bpy.data.worlds.new("world")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.70, 0.86, 1.0, 1.0)
    bg.inputs[1].default_value = 0.7
    # key sun (warm, very soft) high overhead so shadows are short & diffuse
    bpy.ops.object.light_add(type="SUN", location=(5, -5, 12))
    sun = bpy.context.active_object
    sun.data.energy = 3.6
    sun.data.angle = math.radians(14)
    sun.data.color = (1.0, 0.97, 0.92)
    sun.rotation_euler = (math.radians(62), math.radians(6), math.radians(-30))
    # small cool sky fill from the opposite side
    bpy.ops.object.light_add(type="AREA", location=(-6, 4, 7))
    fill = bpy.context.active_object
    fill.data.energy = 25.0
    fill.data.size = 14
    fill.data.color = (0.85, 0.92, 1.0)
    fill.rotation_euler = (math.radians(60), 0, math.radians(40))


def setup_camera():
    cam_data = bpy.data.cameras.new("iso_cam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = 15.2
    cam = bpy.data.objects.new("iso_cam", cam_data)
    bpy.context.collection.objects.link(cam)
    cam.location = (13.0, -13.0, 13.0)
    cam.rotation_euler = (math.radians(54.736), 0, math.radians(45))
    bpy.context.scene.camera = cam
    return cam


# ----------------------------------------------------------------------------
# Island + pond
# ----------------------------------------------------------------------------
def build_island():
    # Rounded dirt underbelly (a flattened sphere = cute floating island).
    sphere("dirt", (0, 0, -2.6), 1.0, M["dirt"],
           scale=(6.7, 6.7, 2.6), seg=48, ring=28)
    # Puffy grass DISK: flat top at z=0 (so rides sit on it), rounded edges
    # that roll down toward the dirt. Built as a cylinder + big bevel.
    g = cyl("grass", (0, 0, -0.28), 6.7, 0.56, M["grass"], verts=72)
    _bevel(g, 0.42, 4)
    _smooth(g)
    # pond cutter (boolean hole through the grass)
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=64, radius=2.5, depth=4.0, location=(0, 0.35, -0.3))
    cutter = bpy.context.active_object
    cutter.name = "pond_cutter"
    boolmod = g.modifiers.new("pond", "BOOLEAN")
    boolmod.operation = "DIFFERENCE"
    boolmod.object = cutter
    boolmod.solver = "EXACT"
    cutter.hide_render = True
    cutter.hide_viewport = True
    # water (top just below the grass surface at z=0)
    cyl("water", (0, 0.35, -0.18), 2.35, 0.4, M["water"], verts=64)
    # sandy bank — a flat torus lying in the XY plane around the pond
    torus("sand_bank", (0, 0.35, 0.02), 2.42, 0.22, M["sand"],
          seg=72, ring=14)


# ----------------------------------------------------------------------------
# Path (cute rounded tiles along a superellipse loop)
# ----------------------------------------------------------------------------
def superellipse(t, a, b, n=4.0):
    ct, st = math.cos(t), math.sin(t)
    x = a * math.copysign(abs(ct) ** (2.0 / n), ct)
    y = b * math.copysign(abs(st) ** (2.0 / n), st)
    return x, y


def _ribbon_ring(name, center_fn, n, half_w, z, mat, closed=True):
    """Build a flat ribbon mesh following a 2D loop of points."""
    pts = [center_fn(2 * math.pi * i / n) for i in range(n)]
    verts = []
    for i, (x, y) in enumerate(pts):
        xp, yp = pts[(i - 1) % n]
        xn, yn = pts[(i + 1) % n]
        tx, ty = xn - xp, yn - yp
        ln = math.hypot(tx, ty) or 1.0
        tx, ty = tx / ln, ty / ln
        nx, ny = -ty, tx  # outward normal (for a CCW loop)
        verts.append((x + nx * half_w, y + ny * half_w, z + 0.06))  # 0 outer top
        verts.append((x - nx * half_w, y - ny * half_w, z + 0.06))  # 1 inner top
        verts.append((x + nx * half_w, y + ny * half_w, z - 0.06))  # 2 outer bot
        verts.append((x - nx * half_w, y - ny * half_w, z - 0.06))  # 3 inner bot
    faces = []
    last = n if closed else n - 1
    for i in range(last):
        o1 = 4 * ((i + 1) % n)
        o0 = 4 * i
        ot0, it0, ob0, ib0 = o0, o0 + 1, o0 + 2, o0 + 3
        ot1, it1, ob1, ib1 = o1, o1 + 1, o1 + 2, o1 + 3
        # correct CCW winding for outward-facing / up-facing faces
        faces.append((ot0, ot1, it1, it0))          # top (CCW -> +Z)
        faces.append((ob0, ib0, ib1, ob1))          # bottom (CW -> -Z)
        faces.append((ot0, ob0, ob1, ot1))          # outer side
        faces.append((it0, it1, ib1, ib0))          # inner side
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    _smooth(obj)
    # soft rounded edge without the weighted-normal that caused dark facets
    b = obj.modifiers.new("bev_edge", "BEVEL")
    b.width = 0.04
    b.segments = 2
    b.limit_method = "ANGLE"
    b.angle_limit = math.radians(35)
    return obj


def build_path():
    # A single wide, continuous rounded loop around the pond. Rides sit just
    # outside it, so there are no T-junctions (which previously caused
    # Z-fighting black diamonds where spur ribbons overlapped the ring).
    a, b = 4.35, 3.95
    _ribbon_ring("path_loop", lambda t: superellipse(t, a, b),
                 n=72, half_w=0.62, z=0.0, mat=M["path"])


# ----------------------------------------------------------------------------
# Rides
# ----------------------------------------------------------------------------
def build_ferris(pos):
    cx, cy = pos
    grp = bpy.data.objects.new("ferris_group", None)
    bpy.context.collection.objects.link(grp)
    # A-frame legs
    apex = Vector((cx, cy, 3.7))
    for sgn in (-1, 1):
        cyl_between((cx + sgn * 0.9, cy - 1.0, 0.05), apex, 0.12,
                    M["cream"], f"ferris_leg_{sgn}")
        cyl_between((cx + sgn * 0.9, cy + 1.0, 0.05), apex, 0.12,
                    M["cream"], f"ferris_leg_b_{sgn}")
    # base cross bar
    cyl_between((cx - 1.1, cy, 0.05), (cx + 1.1, cy, 0.05), 0.08,
                M["gold"], "ferris_base")
    # wheel
    R = 2.25
    wheel = torus("ferris_wheel", apex, R, 0.08, M["coral"],
                  rot=(math.radians(90) - math.radians(12), 0, 0))
    # hub
    hub = cyl("ferris_hub", apex, 0.28, 0.25, M["gold"],
              rot=(math.radians(90), 0, 0), verts=20)
    # spokes
    n = 8
    spoke_color = [M["yellow"], M["mint"], M["pink"], M["lilac"]]
    for i in range(n):
        ang = 2 * math.pi * i / n - math.radians(12)
        p = (cx + R * math.cos(ang), cy + R * math.sin(ang), apex.z)
        cyl_between(apex, p, 0.045, M["cream"], f"spoke_{i}", verts=8)
    # gondolas (hang upright)
    tilt = -math.radians(12)
    gond_colors = [M["yellow"], M["mint"], M["pink"], M["lilac"],
                   M["coral"], M["sky"], M["cream"], M["mint"]]
    for i in range(n):
        ang = 2 * math.pi * i / n + tilt
        rim = Vector((cx + R * math.cos(ang), cy + R * math.sin(ang),
                      apex.z))
        top = rim - Vector((0, 0, 0.35))
        hanger = cyl_between(rim, top, 0.025, M["cream"],
                             f"hanger_{i}", verts=6)
        g = box(f"gondola_{i}",
                (top.x, top.y, top.z - 0.22), (0.55, 0.5, 0.4),
                gond_colors[i], bev=0.12)
        # little window
        box(f"gondola_win_{i}", (top.x, top.y + 0.26, top.z - 0.22),
            (0.34, 0.04, 0.22), M["glass"], bev=0.04, smooth=False)
    # flag on top
    cyl_between(apex, apex + Vector((0, 0, 0.9)), 0.03, M["cream"],
                "ferris_pole", verts=6)


def build_carousel(pos):
    cx, cy = pos
    # base
    cyl("carousel_base", (cx, cy, 0.2), 1.45, 0.35, M["cream"], verts=40)
    cyl("carousel_band", (cx, cy, 0.34), 1.48, 0.12, M["red"], verts=40)
    # center pole
    cyl("carousel_pole", (cx, cy, 1.3), 0.07, 2.4, M["gold"], verts=16)
    # tent (cone)
    cone("carousel_tent", (cx, cy, 2.25), 1.55, 0.12, 1.9, M["red"],
         verts=40)
    # cream stripes on tent
    for i in range(10):
        ang = 2 * math.pi * i / 10
        x = cx + 0.95 * math.cos(ang)
        y = cy + 0.95 * math.sin(ang)
        cyl_between((x, y, 1.35), (cx, cy, 3.15), 0.06,
                    M["cream"], f"tent_stripe_{i}", verts=6)
    # finial
    sphere("carousel_finial", (cx, cy, 3.3), 0.18, M["gold"], seg=16, ring=12)
    # horses on poles
    horse_cols = [M["white"], M["pink"], M["mint"], M["yellow"]]
    for i in range(4):
        ang = math.radians(45 + i * 90)
        r = 0.95
        x = cx + r * math.cos(ang)
        y = cy + r * math.sin(ang)
        # pole
        cyl(f"horse_pole_{i}", (x, y, 0.95), 0.04, 1.6, M["gold"], verts=8)
        # body
        b = box(f"horse_body_{i}", (x, y, 1.05), (0.55, 0.28, 0.34),
                horse_cols[i], bev=0.12)
        # head
        hx = x + 0.30 * math.cos(ang)
        hy = y + 0.30 * math.sin(ang)
        box(f"horse_head_{i}", (hx, hy, 1.25), (0.22, 0.22, 0.30),
            horse_cols[i], bev=0.10,
            rot=(0, 0, math.atan2(math.sin(ang), math.cos(ang))))
        # ears
        box(f"horse_ear_{i}", (hx, hy, 1.45), (0.06, 0.06, 0.12),
            horse_cols[i], bev=0.03)
        # mane (tiny coral)
        box(f"horse_mane_{i}", (x, y, 1.28), (0.5, 0.10, 0.12),
            M["coral"], bev=0.04)


def build_coaster(center=(-3.9, -2.3)):
    """A small elevated oval coaster in its own pocket at front-left."""
    cx, cy = center
    track_z = 1.25
    R = 1.15
    # tubular track via a NURBS circle (slightly oval by squashing Y)
    curve = bpy.data.curves.new("coaster_track", "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = 0.07
    curve.bevel_resolution = 5
    spline = curve.splines.new("NURBS")
    npts = 28
    spline.points.add(npts - 1)
    spline.use_cyclic_u = True
    spline.order_u = 3
    for i, p in enumerate(spline.points):
        t = 2 * math.pi * i / npts
        p.co = (cx + R * math.cos(t),
                cy + R * 0.82 * math.sin(t),
                track_z + 0.12 * math.sin(2 * t), 1)
    track = bpy.data.objects.new("coaster_track", curve)
    bpy.context.collection.objects.link(track)
    track.data.materials.append(M["coral"])
    # a little raised green coaster pad so it reads as its own zone
    cyl("coaster_pad", (cx, cy, 0.08), 1.55, 0.18, M["grass2"], verts=32)
    # supports
    n_sup = 8
    for i in range(n_sup):
        t = 2 * math.pi * i / n_sup + 0.2
        x = cx + (R - 0.15) * math.cos(t)
        y = cy + R * 0.82 * math.sin(t)
        cyl_between((x, y, 0.1), (x, y, track_z - 0.12), 0.055,
                    M["cream"], f"support_{i}", verts=8)
    # little 3-car Nessie train on the track (front side, facing camera-ish)
    car_cols = [M["yellow"], M["mint"], M["lilac"]]
    start_t = math.radians(-110)
    for k in range(3):
        t = start_t + k * math.radians(22)
        x = cx + (R - 0.05) * math.cos(t)
        y = cy + (R * 0.82 - 0.05) * math.sin(t)
        z = track_z + 0.12 * math.sin(2 * t)
        # tangent yaw: derivative (-R sin t, R*0.82 cos t)
        yaw = math.atan2(R * 0.82 * math.cos(t), -R * math.sin(t))
        box(f"car_{k}", (x, y, z + 0.16), (0.42, 0.34, 0.30),
            car_cols[k], bev=0.11, rot=(0, 0, yaw))
        # front car gets a little Nessie fin + face
        if k == 0:
            fx = x + 0.24 * math.cos(yaw)
            fy = y + 0.24 * math.sin(yaw)
            cone("car_fin", (fx, fy, z + 0.42), 0.10, 0.02, 0.24,
                 M["nessie"],
                 rot=(0, math.radians(90) - yaw, 0), verts=12)
            ex = x + 0.16 * math.cos(yaw)
            ey = y + 0.16 * math.sin(yaw)
            for sgn in (-1, 1):
                nx = ex + sgn * 0.10 * math.cos(yaw - 1.57)
                ny = ey + sgn * 0.10 * math.sin(yaw - 1.57)
                sphere(f"car_eye_{sgn}", (nx, ny, z + 0.28), 0.045,
                       M["white"], seg=10, ring=8)
                sphere(f"car_pupil_{sgn}", (nx, ny, z + 0.26), 0.022,
                       M["black"], seg=8, ring=6)


# ----------------------------------------------------------------------------
# Stalls
# ----------------------------------------------------------------------------
def build_icecream(pos):
    x, y = pos
    # booth
    box("ic_booth", (x, y, 0.55), (1.5, 1.1, 1.0), M["mint"], bev=0.16)
    # counter top
    box("ic_counter", (x, y + 0.0, 1.15), (1.6, 1.2, 0.16), M["cream"],
        bev=0.08)
    # striped awning (curved front)
    box("ic_awning", (x, y + 0.55, 1.0), (1.7, 0.5, 0.22), M["red"],
        bev=0.12)
    for i in range(6):
        sx = x - 0.6 + i * 0.24
        box(f"ic_awstripe_{i}", (sx, y + 0.78, 1.0), (0.10, 0.20, 0.24),
            M["white"], bev=0.04)
    # giant soft-serve on the roof
    cone("ic_cone", (x, y, 1.75), 0.22, 0.0, 0.55, M["gold"], verts=16)
    sphere("ic_swirl1", (x, y, 2.15), 0.26, M["white"], seg=20, ring=14)
    sphere("ic_swirl2", (x, y * 1.0, 2.40), 0.20, M["pink"], seg=20, ring=14)
    sphere("ic_swirl3", (x, y, 2.60), 0.14, M["white"], seg=16, ring=12)
    sphere("ic_cherry", (x, y, 2.78), 0.09, M["red"], seg=12, ring=10)


def build_entrance(pos):
    x, y = pos
    # ticket booth
    box("tk_booth", (x + 2.0, y + 0.2, 0.5), (1.2, 1.0, 0.9),
        M["lilac"], bev=0.15)
    box("tk_window", (x + 2.0, y + 0.72, 0.6), (0.8, 0.05, 0.45),
        M["glass"], bev=0.05, smooth=False)
    box("tk_roof", (x + 2.0, y + 0.2, 1.05), (1.4, 1.2, 0.16),
        M["cream"], bev=0.08)
    sphere("tk_nob", (x + 1.45, y + 0.72, 0.45), 0.05, M["gold"],
           seg=10, ring=8)
    # arch posts
    cyl("arch_post_l", (x - 1.3, y, 1.1), 0.16, 2.2, M["cream"], verts=16)
    cyl("arch_post_r", (x + 1.3, y, 1.1), 0.16, 2.2, M["cream"], verts=16)
    # arch top beam
    box("arch_top", (x, y, 2.35), (3.2, 0.5, 0.5), M["red"], bev=0.2)
    box("arch_stripe", (x, y, 2.35), (3.3, 0.12, 0.52), M["white"],
        bev=0.06)
    # flags
    for sgn in (-1, 1):
        fx = x + sgn * 1.3
        cyl_between((fx, y, 2.6), (fx, y, 3.3), 0.025, M["cream"],
                    f"flagpole_{sgn}", verts=6)
        cone(f"flag_{sgn}", (fx + sgn * 0.18, y, 3.1), 0.18, 0.0, 0.26,
             M["yellow"] if sgn < 0 else M["mint"],
             rot=(0, math.radians(90), 0), verts=3)
    # a little Nessie face plaque on the arch
    sphere("arch_nessie", (x, y, 2.05), 0.22, M["nessie"], seg=16, ring=12,
           scale=(1.0, 0.4, 1.0))
    for sgn in (-1, 1):
        sphere(f"arch_eye_{sgn}", (x + sgn * 0.07, y + 0.12, 2.12),
               0.04, M["black"], seg=8, ring=6)


# ----------------------------------------------------------------------------
# Nessie centerpiece (metaballs -> merged puffy blob) + face
# ----------------------------------------------------------------------------
def build_nessie():
    bpy.ops.object.metaball_add(type="BALL", location=(0, 0.35, 0.0))
    mball = bpy.context.active_object.data
    mball.name = "nessie_body"
    mball.resolution = 0.12
    mball.render_resolution = 0.08
    mball.materials.append(M["nessie"])
    # Chain of balls forming a friendly S-curve through the pond. The HEAD is
    # on the -Y (front/near-camera) side so the face shows in the isometric
    # view; the tail curls away to the back. Y is offset by POND_Y=0.35.
    # The camera/entrance is on the -Y side, so the HEAD sits at the front of
    # the pond (y < 0) and the body/humps curl away to the back-left. Water
    # surface is ~z=0.0; the body rides half-submerged while the humps, neck
    # and head break the surface.
    chain = [
        # (x, y, z, radius)
        (-1.70, 1.45, -0.05, 0.46),  # tail tip curl (back-left)
        (-1.35, 0.95, 0.02, 0.58),   # tail
        (-0.85, 0.35, 0.12, 0.78),   # hump 3
        (-0.20, -0.05, 0.15, 0.84),  # hump 1 (biggest, back-center)
        (0.55, 0.15, 0.10, 0.66),    # hump 2
        (1.10, -0.10, 0.06, 0.58),   # dip toward neck
        (1.30, -0.65, 0.28, 0.56),   # neck base
        (1.10, -1.15, 0.60, 0.62),   # neck rising
        (0.70, -1.50, 0.92, 0.80),   # HEAD (front, faces camera at -Y)
    ]
    # clear the default element then add ours
    mball.elements.clear()
    for (x, y, z, r) in chain:
        el = mball.elements.new(type="BALL")
        el.co = (x, y, z)
        el.radius = r
    # select + convert metaball to mesh (conversion replaces the object)
    obj = bpy.context.active_object
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.convert(target="MESH")
    nessie = bpy.context.active_object
    nessie.name = "nessie"
    _bevel(nessie, 0.04, 2)
    # belly accent (lighter) — a flattened patch on the front of the body
    sphere("nessie_belly", (-0.1, 0.3, -0.05), 0.85, M["nessie_b"],
           scale=(1.6, 1.0, 0.35), seg=20, ring=14)
    # face on the head (center ~ (0.70, -1.50, 0.92)); front faces -Y
    hx, hy, hz = 0.70, -1.50, 0.92
    for sgn in (-1, 1):
        sphere(f"nessie_eye_{sgn}",
               (hx + sgn * 0.23, hy - 0.02, hz + 0.23), 0.19,
               M["white"], seg=18, ring=14)
        sphere(f"nessie_pupil_{sgn}",
               (hx + sgn * 0.25, hy - 0.11, hz + 0.20), 0.10,
               M["black"], seg=14, ring=12)
        sphere(f"nessie_spark_{sgn}",
               (hx + sgn * 0.28, hy - 0.15, hz + 0.25), 0.04,
               M["white"], seg=8, ring=6)
    for sgn in (-1, 1):
        sphere(f"nessie_blush_{sgn}",
               (hx + sgn * 0.38, hy - 0.04, hz - 0.06), 0.12,
               M["pink"], scale=(1, 0.4, 0.8), seg=14, ring=10)
    # smile — small torus arc facing the camera
    smile = torus("nessie_smile", (hx, hy - 0.10, hz - 0.24), 0.22, 0.03,
                  M["black"], seg=18, ring=8)
    smile.scale = (1.0, 0.55, 1.0)
    for sgn in (-1, 1):
        sphere(f"nessie_nostril_{sgn}",
               (hx + sgn * 0.08, hy - 0.23, hz + 0.08), 0.03,
               M["black"], seg=8, ring=6)
    # dorsal bumps along the back humps (bz from chain)
    for k, (bx, by, bz, br) in enumerate([
        (-0.20, -0.05, 0.15, 0.84), (-0.85, 0.35, 0.12, 0.78),
        (0.55, 0.15, 0.10, 0.66), (1.30, -0.65, 0.28, 0.56)
    ]):
        cone(f"nessie_bump_{k}", (bx, by, bz + br * 0.82), 0.11, 0.0,
             0.24, M["nessie_b"], verts=10)
    # water spout arcing up from behind the head
    sx, sy = hx + 0.15, hy + 0.25
    cyl_between((sx, sy, hz + 0.55), (sx, sy, hz + 1.35), 0.07, M["spout"],
                "nessie_spout", verts=12)
    for k in range(6):
        dx = random.uniform(-0.25, 0.35)
        dy = random.uniform(-0.20, 0.15)
        dz = random.uniform(1.0, 1.5)
        sphere(f"spout_drop_{k}", (sx + dx, sy + dy, hz + dz),
               random.uniform(0.06, 0.12), M["spout"], seg=10, ring=8)


# ----------------------------------------------------------------------------
# Scenery
# ----------------------------------------------------------------------------
def build_tree(x, y, scale=1.0, kind="round"):
    cyl(f"trunk_{x}_{y}", (x, y, 0.4 * scale), 0.11 * scale,
        0.8 * scale, M["bark"], verts=10)
    if kind == "round":
        sphere(f"leaf1_{x}_{y}", (x, y, 1.15 * scale), 0.6 * scale,
               M["leaf"], seg=18, ring=14)
        sphere(f"leaf2_{x}_{y}", (x + 0.3 * scale, y + 0.1 * scale,
                                  1.0 * scale), 0.4 * scale,
               M["leaf2"], seg=16, ring=12)
    else:
        cone(f"leaf_{x}_{y}", (x, y, 1.3 * scale), 0.55 * scale,
             0.0, 1.3 * scale, M["leaf"], verts=14)
        cone(f"leaf2_{x}_{y}", (x, y, 1.7 * scale), 0.4 * scale,
             0.0, 0.9 * scale, M["leaf2"], verts=14)


def build_bush(x, y, s=1.0):
    sphere(f"bush_{x}_{y}", (x, y, 0.25 * s), 0.32 * s, M["leaf2"],
           seg=14, ring=10)
    sphere(f"bush2_{x}_{y}", (x + 0.22 * s, y + 0.1 * s, 0.22 * s),
           0.22 * s, M["leaf"], seg=12, ring=9)


def build_flower(x, y, col):
    cyl(f"fstem_{x}_{y}", (x, y, 0.12), 0.02, 0.22, M["leaf"], verts=6)
    sphere(f"fhead_{x}_{y}", (x, y, 0.26), 0.09, col, seg=10, ring=8)
    sphere(f"fcenter_{x}_{y}", (x, y, 0.27), 0.04, M["yellow"],
           seg=8, ring=6)


def build_bench(x, y, yaw):
    box(f"bench_seat_{x}_{y}", (x, y, 0.32), (0.9, 0.32, 0.10),
        M["brown"], bev=0.06, rot=(0, 0, yaw))
    box(f"bench_back_{x}_{y}", (x - 0.35 * math.sin(yaw), y + 0.35 * math.cos(yaw),
                                0.55), (0.9, 0.10, 0.45),
        M["brown"], bev=0.06, rot=(0, 0, yaw))
    for sgn in (-1, 1):
        box(f"bench_leg_{x}_{y}_{sgn}",
            (x + sgn * 0.32 * math.cos(yaw), y + sgn * 0.32 * math.sin(yaw),
             0.13), (0.10, 0.28, 0.24), M["cream"], bev=0.04)


def build_lamp(x, y):
    cyl(f"lamp_post_{x}_{y}", (x, y, 0.8), 0.05, 1.6, M["cream"], verts=10)
    sphere(f"lamp_ball_{x}_{y}", (x, y, 1.7), 0.18, M["lamp"], seg=16,
           ring=12)
    cyl_between((x, y, 1.55), (x, y, 1.78), 0.025, M["cream"],
                f"lamp_cap_{x}_{y}", verts=6)


def build_cloud(x, y, z, s=1.0):
    for (dx, dy, dz, r) in [
        (0, 0, 0, 0.55), (0.5, 0.1, 0.05, 0.45),
        (-0.5, 0.05, 0.0, 0.42), (0.15, -0.2, 0.1, 0.4),
        (0.0, 0.2, 0.12, 0.38)
    ]:
        sp = sphere(f"cloud_{x}_{y}_{dx}_{dy}",
                    (x + dx * s, y + dy * s, z + dz * s), r * s,
                    M["white"], seg=18, ring=14)


def build_visitor(pos):
    x, y, yaw = pos
    # group
    g = bpy.data.objects.new("visitor", None)
    bpy.context.collection.objects.link(g)
    # legs (one forward = walking)
    l1 = box("v_leg_l", (x - 0.09, y, 0.28), (0.16, 0.18, 0.46),
             M["denim"], bev=0.06)
    l2 = box("v_leg_r", (x + 0.09, y + 0.08, 0.28), (0.16, 0.18, 0.46),
             M["denim"], bev=0.06, rot=(0.15, 0, 0))
    # shoes
    box("v_shoe_l", (x - 0.09, y + 0.02, 0.06), (0.18, 0.26, 0.12),
        M["black"], bev=0.05)
    box("v_shoe_r", (x + 0.09, y + 0.16, 0.06), (0.18, 0.26, 0.12),
        M["black"], bev=0.05, rot=(0.15, 0, 0))
    # body
    body = box("v_body", (x, y, 0.72), (0.45, 0.30, 0.55),
               M["shirt"], bev=0.14)
    # backpack
    pack = box("v_pack", (x - 0.0, y - 0.22, 0.72), (0.34, 0.18, 0.42),
               M["pack"], bev=0.10)
    # arms
    box("v_arm_l", (x - 0.28, y + 0.02, 0.72), (0.13, 0.15, 0.45),
        M["shirt"], bev=0.08, rot=(0, 0, 0.25))
    box("v_arm_r", (x + 0.28, y + 0.02, 0.72), (0.13, 0.15, 0.45),
        M["shirt"], bev=0.08, rot=(0, 0, -0.4))
    # head
    head = sphere("v_head", (x, y + 0.02, 1.18), 0.26, M["skin"], seg=20,
                  ring=16)
    # cap
    cap = sphere("v_cap", (x, y + 0.02, 1.34), 0.28, M["cap"],
                 scale=(1.0, 1.0, 0.55), seg=18, ring=12)
    box("v_brim", (x, y + 0.24, 1.24), (0.30, 0.18, 0.06),
        M["cap"], bev=0.04)
    # eyes
    for sgn in (-1, 1):
        sphere(f"v_eye_{sgn}", (x + sgn * 0.09, y + 0.22, 1.16), 0.035,
               M["black"], seg=8, ring=6)
    # smile
    torus("v_smile", (x, y + 0.24, 1.05), 0.07, 0.012, M["black"],
          rot=(math.radians(90), 0, 0), seg=12, ring=6)
    # parent every visitor part to the group, placed at the visitor's feet,
    # then rotate the whole group to face yaw (keeps world positions).
    g.location = (x, y, 0.0)
    bpy.context.view_layer.update()
    inv = g.matrix_world.inverted()
    for o in bpy.data.objects:
        if o.name.startswith("v_") and o.parent is None:
            o.parent = g
            o.matrix_parent_inverse = inv
    g.rotation_euler = (0, 0, yaw)


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def build():
    reset()
    init_materials()
    setup_camera()
    build_island()
    build_path()
    build_nessie()
    build_coaster((-3.9, -2.4))
    build_ferris((-3.9, 3.7))
    build_carousel((3.9, 3.6))
    build_icecream((5.1, 0.2))
    build_entrance((0.0, -4.5))

    # scenery (kept off the pond radius ~2.35 at y+0.35 and the coaster pad)
    tree_spots = [(-5.3, -4.4, 1.0, "round"), (-5.6, 1.4, 0.95, "cone"),
                  (5.0, -3.6, 1.05, "round"), (3.0, -4.6, 0.8, "round"),
                  (-2.4, -5.0, 0.85, "cone"), (5.4, 3.2, 0.85, "round"),
                  (-5.4, -0.2, 0.8, "round"), (4.2, 4.7, 0.9, "cone"),
                  (0.6, 5.1, 0.8, "round")]
    for (x, y, s, k) in tree_spots:
        build_tree(x, y, s, k)

    bush_spots = [(-2.6, 2.9), (2.6, -3.8), (-5.0, -3.6), (4.0, -1.8),
                  (-1.7, 4.5), (2.1, 4.6), (-4.9, 2.4), (5.2, 1.9),
                  (1.6, -4.6), (-1.4, -4.2)]
    for (x, y) in bush_spots:
        build_bush(x, y, random.uniform(0.8, 1.2))

    flower_cols = [M["pink"], M["yellow"], M["lilac"], M["coral"], M["white"]]
    for _ in range(26):
        a = random.uniform(0, 2 * math.pi)
        r = random.uniform(2.7, 5.9)
        x, y = r * math.cos(a), r * math.sin(a)
        # keep flowers off the pond
        if (x) ** 2 + (y - 0.35) ** 2 < 2.4 ** 2:
            continue
        build_flower(x, y, random.choice(flower_cols))

    # benches + lamps along the path (benches sit on the grass just outside
    # the path ring so their shadows don't cut across the path)
    build_bench(4.7, 1.4, math.radians(-110))
    build_bench(-4.4, -2.9, math.radians(70))
    build_bench(-0.4, 4.6, math.radians(180))
    build_bench(2.0, -4.2, math.radians(-20))
    build_lamp(3.6, 0.2)
    build_lamp(-3.5, 0.3)
    build_lamp(0.4, 3.5)
    build_lamp(0.2, -3.6)
    build_lamp(-3.0, -2.8)
    build_lamp(3.2, -2.6)

    # clouds
    build_cloud(-5.5, -3.0, 6.3, 1.0)
    build_cloud(5.0, 2.5, 6.9, 0.85)
    build_cloud(0.0, -6.0, 6.6, 0.8)

    # visitor on the front path loop, facing toward Nessie (+y)
    build_visitor((0.0, -3.95, math.radians(0)))


def render_png(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def export_glb(path):
    bpy.ops.object.select_all(action="DESELECT")
    for o in bpy.data.objects:
        if o.type == "MESH":
            o.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=path,
        export_format="GLB",
        export_apply=True,
        export_animations=False,
        export_yup=True,
        use_selection=True,
    )


if __name__ == "__main__":
    build()
    png = os.path.join(OUT, "nessie_park.png")
    glb = os.path.join(OUT, "nessie_park.glb")
    print(f"[nessie] rendering -> {png}", flush=True)
    render_png(png)
    print(f"[nessie] exporting -> {glb}", flush=True)
    export_glb(glb)
    print(f"[nessie] done. png={os.path.getsize(png)} glb={os.path.getsize(glb)}",
          flush=True)
