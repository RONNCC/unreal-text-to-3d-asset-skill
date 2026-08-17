# -*- coding: utf-8 -*-
"""Render a preview PNG of a GLB with headless Blender (Cycles, CPU).

Used to produce docs/images/*.png — proof that the GLB assets in this repo are
real geometry that loads and renders. CPU Cycles needs no GPU and no GL context,
so it works in CI-style sandboxes too.

    python3 examples/fixtures/render_preview.py <in.glb> <out.png>
"""
import math
import os
import sys

import bpy


def add_camera(target=(0, 0, 0.9), dist=7.0, angle=math.radians(55)):
    x = dist * math.cos(angle)
    y = -dist * math.sin(angle)
    z = 3.6
    bpy.ops.object.camera_add(location=(x, y, z))
    cam = bpy.context.active_object
    direction = [target[i] - c for i, c in enumerate(cam.location)]
    # point camera at target
    import mathutils
    cam.rotation_euler = mathutils.Vector(direction).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = cam


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    src, dst = argv[0], argv[1]

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=src)
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    print("PREVIEW_MESHES:", [o.name for o in meshes])

    # ground
    bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, 0))
    plane = bpy.context.active_object
    pm = bpy.data.materials.new("ground")
    pm.diffuse_color = (0.8, 0.8, 0.8, 1.0)
    plane.data.materials.append(pm)

    # light
    bpy.ops.object.light_add(type="SUN", location=(4, -4, 8))
    sun = bpy.context.active_object
    sun.data.energy = 3.0
    sun.rotation_euler = (math.radians(35), math.radians(-20), math.radians(30))
    bpy.ops.object.light_add(type="AREA", location=(-4, 2, 6))
    area = bpy.context.active_object
    area.data.energy = 400.0
    area.data.size = 5.0

    add_camera()

    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 48
    scene.render.resolution_x = 640
    scene.render.resolution_y = 480
    scene.render.filepath = os.path.abspath(dst)
    # neutral world
    bpy.data.worlds.new("W")
    scene.world = bpy.data.worlds["W"]
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.9, 0.92, 0.95, 1.0)
    bg.inputs[1].default_value = 0.6

    bpy.ops.render.render(write_still=True)
    print("PREVIEW_DONE ->", scene.render.filepath)


if __name__ == "__main__":
    main()
