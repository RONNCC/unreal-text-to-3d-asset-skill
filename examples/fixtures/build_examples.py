# -*- coding: utf-8 -*-
"""Build the example stand-in assets with Blender (bpy) and export them as GLB.

These are NOT AI outputs — they are small procedural meshes that stand in for a
Hunyuan3D-2 result so the downstream stages (GLB -> FBX -> validation -> render)
can be exercised byte-for-byte on any machine, without a GPU. The real pipeline
substitutes `hunyuan_gen.py`'s output for these files; everything after that is
identical.

Run (see MANIFEST.md for the exact validated invocation):
    blender-or-bpy python examples/fixtures/build_examples.py
"""
import math
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "tests", "fixtures"))
from make_fixtures import write_png  # reuse the pure-python PNG writer


def make_uv_texture(material, png_path):
    """Give a material an image texture so GLB/FBX texture embedding is exercised."""
    img = bpy.data.images.load(png_path)
    mat = material
    nodes = mat.node_tree.nodes
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = img
    mat.node_tree.links.new(tex.outputs["Color"], nodes["Principled BSDF"].inputs["Base Color"])


def uv_unwrap(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.cube_project()
    bpy.ops.object.mode_set(mode="OBJECT")


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def mat(name, rgb):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.7
    return m


def box(name, loc, scale, material):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = (scale[0] / 2, scale[1] / 2, scale[2] / 2)
    bpy.ops.object.transform_apply(scale=True)
    o.data.materials.append(material)
    return o


def cyl(name, loc, radius, depth, material, rot_y=0.0, verts=20):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius, depth=depth, location=loc)
    o = bpy.context.active_object
    o.name = name
    if rot_y:
        o.rotation_euler[1] = rot_y
        bpy.ops.object.transform_apply(rotation=True)
    o.data.materials.append(material)
    return o


def join(objs, name):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    bpy.context.active_object.name = name
    return bpy.context.active_object


def export_glb(path):
    bpy.ops.export_scene.gltf(
        filepath=path,
        export_format="GLB",
        export_apply=True,
        export_animations=False,
    )
    return os.path.getsize(path)


def build_locomotive():
    """Boxy stylized steam locomotive (~Thomas-proportioned), multi-material."""
    reset_scene()
    green = mat("loco_green", (0.13, 0.35, 0.16))
    black = mat("loco_black", (0.05, 0.05, 0.05))
    red = mat("loco_red", (0.55, 0.08, 0.06))
    brass = mat("loco_brass", (0.55, 0.4, 0.15))
    parts = [
        box("frame", (0, 0, 0.55), (3.4, 1.15, 0.25), black),
        cyl("boiler", (0.25, 0, 1.15), 0.55, 2.3, green, rot_y=math.pi / 2),
        box("cab", (-1.25, 0, 1.35), (0.85, 1.15, 1.35), green),
        cyl("chimney", (1.25, 0, 1.95), 0.16, 0.6, black),
        cyl("dome", (0.35, 0, 1.75), 0.2, 0.3, brass),
        box("bufferbeam", (1.7, 0, 0.6), (0.12, 1.2, 0.35), red),
    ]
    for x in (-1.0, 0.0, 1.0):
        for y in (-0.62, 0.62):
            parts.append(cyl(f"wheel_{x:+.0f}_{y:+.0f}", (x, y, 0.4), 0.4, 0.14,
                             red, rot_y=math.pi / 2, verts=16))
    loco = join(parts, "LocomotiveStandIn")
    uv_unwrap(loco)
    png = os.path.join(HERE, "boiler_gradient.png")
    if not os.path.isfile(png):
        write_png(png)  # deterministic 256x256 gradient texture
    make_uv_texture(green, png)
    path = os.path.join(HERE, "Locomotive_textured.glb")
    return path, export_glb(path)


def build_wagon():
    """Simple open goods wagon."""
    reset_scene()
    wood = mat("wagon_wood", (0.36, 0.22, 0.10))
    gray = mat("wagon_iron", (0.15, 0.16, 0.17))
    parts = [
        box("bed", (0, 0, 0.55), (2.2, 1.1, 0.15), gray),
        box("side_l", (0, 0.53, 0.9), (2.2, 0.08, 0.6), wood),
        box("side_r", (0, -0.53, 0.9), (2.2, 0.08, 0.6), wood),
        box("end_f", (1.06, 0, 0.9), (0.08, 1.1, 0.6), wood),
        box("end_b", (-1.06, 0, 0.9), (0.08, 1.1, 0.6), wood),
    ]
    for x in (-0.65, 0.65):
        for y in (-0.57, 0.57):
            parts.append(cyl(f"wheel_{x:+.2f}_{y:+.2f}", (x, y, 0.35), 0.35, 0.12,
                             gray, rot_y=math.pi / 2, verts=16))
    wagon = join(parts, "WagonStandIn")
    path = os.path.join(HERE, "Wagon_textured.glb")
    return path, export_glb(path)


if __name__ == "__main__":
    for builder in (build_locomotive, build_wagon):
        path, size = builder()
        print(f"[fixtures] wrote {path} ({size/1024:.0f} KB)")
