# -*- coding: utf-8 -*-
"""Convert a GLB to FBX with embedded textures, headless via Blender.

  blender --background \\
    --python glb_to_fbx.py -- --src asset.glb --dst asset.fbx

On macOS, run it through the provided container instead of a local Blender install:

  bin/glb_to_fbx.sh asset.glb asset.fbx   # docker compose run --rm blender-fbx ...

The FBX is what Unreal's unreal-mcp StaticMeshTools.import_file accepts (it rejects .glb).
"""
import bpy, sys, argparse

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--src", required=True)
ap.add_argument("--dst", required=True)
a = ap.parse_args(argv)

# Empty scene (no default cube/camera/light)
bpy.ops.wm.read_factory_settings(use_empty=True)

bpy.ops.import_scene.gltf(filepath=a.src)
print("IMPORTED_MESHES:", [o.name for o in bpy.data.objects if o.type == "MESH"], flush=True)

bpy.ops.export_scene.fbx(
    filepath=a.dst,
    use_selection=False,
    path_mode="COPY",        # required with embed_textures
    embed_textures=True,     # pack textures inside the .fbx
    mesh_smooth_type="FACE",
    add_leaf_bones=False,
    bake_space_transform=False,
    object_types={"MESH"},
)
print("BLENDER_EXPORT_DONE ->", a.dst, flush=True)
