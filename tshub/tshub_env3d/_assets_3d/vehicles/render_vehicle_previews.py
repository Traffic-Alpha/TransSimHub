'''
@Author: WANG Maonan
@Date: 2026-07-11
@Description: Render multi-angle preview images for every non-raw vehicle GLB.

Run with Blender from the repository root:
    /home/wmn/blender/blender --background --python \
        tshub/tshub_env3d/_assets_3d/vehicles/render_vehicle_previews.py

Outputs:
    tshub/tshub_env3d/_assets_3d/vehicles/_previews/<category>/<name>.png
'''
from pathlib import Path
import math
import shutil

import bpy
from mathutils import Vector


SCRIPT_DIR = Path(__file__).resolve().parent
OUT_DIR = SCRIPT_DIR / "_previews"
TMP_DIR = OUT_DIR / "_tmp"
TILE_RESOLUTION = 760
TILE_CROP_BOTTOM = 80
SAMPLES = 64
STUDIO_PREFIX = "preview_studio_"
STUDIO_COLOR = (0.58, 0.61, 0.64, 1.0)

VIEW_SPECS = (
    ("front_3quarter", Vector((-0.82, 1.28, 0.46))),
    ("left_side", Vector((-1.45, 0.00, 0.38))),
    ("front", Vector((0.00, 1.55, 0.34))),
    ("rear", Vector((0.00, -1.55, 0.34))),
)


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def configure_render():
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = SAMPLES
    scene.cycles.use_denoising = True
    scene.render.resolution_x = TILE_RESOLUTION
    scene.render.resolution_y = TILE_RESOLUTION
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"

    scene.view_settings.view_transform = "Filmic"
    scene.view_settings.look = "Medium High Contrast"
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1

    world = scene.world or bpy.data.worlds.new("World")
    scene.world = world
    world.color = (0.50, 0.54, 0.58)


def configure_lighting():
    bpy.ops.object.light_add(type="AREA", location=(-4.8, -5.5, 7.5))
    key = bpy.context.object
    key.name = "preview_key_light"
    key.data.energy = 650
    key.data.size = 5.5

    bpy.ops.object.light_add(type="AREA", location=(4.5, 5.0, 5.5))
    fill = bpy.context.object
    fill.name = "preview_fill_light"
    fill.data.energy = 260
    fill.data.size = 8.0

    bpy.ops.object.light_add(type="AREA", location=(0.0, 4.8, 5.0))
    rim = bpy.context.object
    rim.name = "preview_rim_light"
    rim.data.energy = 140
    rim.data.size = 6.0

    bpy.ops.object.light_add(type="AREA", location=(0.0, 0.0, 7.0))
    overhead = bpy.context.object
    overhead.name = "preview_overhead_light"
    overhead.data.energy = 220
    overhead.data.size = 9.0


def mesh_objects():
    return [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]


def mesh_world_bounds(meshes):
    points = []
    for obj in meshes:
        points.extend(obj.matrix_world @ Vector(corner) for corner in obj.bound_box)
    if not points:
        raise RuntimeError("No mesh bounds found")
    min_pt = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    max_pt = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    return min_pt, max_pt


def center_model(meshes):
    min_pt, max_pt = mesh_world_bounds(meshes)
    center = (min_pt + max_pt) * 0.5
    delta = Vector((-center.x, -center.y, -min_pt.z))
    for obj in meshes:
        obj.location += delta
    bpy.context.view_layer.update()
    return mesh_world_bounds(meshes)


def look_at(obj, target: Vector):
    direction = target - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def create_camera(min_pt: Vector, max_pt: Vector):
    dims = max_pt - min_pt
    max_dim = max(dims.x, dims.y, dims.z, 1.0)
    target = Vector((0.0, 0.0, max(dims.z * 0.42, 0.55)))

    bpy.ops.object.camera_add()
    camera = bpy.context.object
    camera.name = "preview_camera"
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = max(max_dim * 1.28, dims.z * 2.0, 3.0)
    camera.data.lens = 70
    bpy.context.scene.camera = camera
    return camera, target, max_dim


def set_camera_view(camera, target: Vector, max_dim: float, direction: Vector):
    direction = direction.normalized()
    camera.location = target + direction * (max_dim * 2.2)
    look_at(camera, target)


def make_principled_material(name: str, color, roughness: float):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    output = nodes.new(type="ShaderNodeOutputMaterial")
    bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
    mat.node_tree.links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = roughness
    if "Metallic" in bsdf.inputs:
        bsdf.inputs["Metallic"].default_value = 0.0
    return mat


def remove_studio_objects():
    for obj in list(bpy.context.scene.objects):
        if obj.name.startswith(STUDIO_PREFIX):
            bpy.data.objects.remove(obj, do_unlink=True)


def orient_to_view(local_point: Vector, right: Vector, back: Vector):
    return right * local_point.x + back * local_point.y + Vector((0.0, 0.0, local_point.z))


def create_studio_set(target: Vector, max_dim: float, view_direction: Vector):
    """Create a curved cyclorama behind the vehicle for the active camera angle."""
    remove_studio_objects()
    view_direction = view_direction.normalized()
    back = Vector((-view_direction.x, -view_direction.y, 0.0))
    if back.length < 1e-6:
        back = Vector((0.0, -1.0, 0.0))
    back.normalize()
    right = Vector((back.y, -back.x, 0.0)).normalized()

    floor_front = max_dim * 7.5
    wall_offset = max_dim * 2.8
    radius = max_dim * 1.25
    wall_height = max_dim * 3.8
    width = max_dim * 8.5

    section = [(Vector((0.0, -floor_front, 0.0)))]
    section.append(Vector((0.0, wall_offset - radius, 0.0)))
    for step in range(1, 13):
        theta = (math.pi * 0.5) * step / 12
        y = wall_offset - radius + math.sin(theta) * radius
        z = radius - math.cos(theta) * radius
        section.append(Vector((0.0, y, z)))
    section.append(Vector((0.0, wall_offset, wall_height)))

    vertices = []
    for x in (-width * 0.5, width * 0.5):
        for point in section:
            world_point = target + orient_to_view(Vector((x, point.y, point.z)), right, back)
            vertices.append(tuple(world_point))

    faces = []
    count = len(section)
    for idx in range(count - 1):
        faces.append((idx, idx + 1, count + idx + 1, count + idx))

    mesh = bpy.data.meshes.new(f"{STUDIO_PREFIX}cyclorama_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    backdrop = bpy.data.objects.new(f"{STUDIO_PREFIX}cyclorama", mesh)
    bpy.context.collection.objects.link(backdrop)
    backdrop.data.materials.append(make_principled_material(
        f"{STUDIO_PREFIX}mat", STUDIO_COLOR, 0.78
    ))

    bevel = backdrop.modifiers.new(f"{STUDIO_PREFIX}soft_sweep", "BEVEL")
    bevel.width = max_dim * 0.035
    bevel.segments = 8
    bevel.affect = "EDGES"
    backdrop.modifiers.new(f"{STUDIO_PREFIX}smooth", "WEIGHTED_NORMAL")


def render_tile(camera, target: Vector, max_dim: float, view_name: str, tile_dir: Path):
    direction = dict(VIEW_SPECS)[view_name]
    set_camera_view(camera, target, max_dim, direction)
    create_studio_set(Vector((0.0, 0.0, 0.0)), max_dim, direction)
    out_path = tile_dir / f"{view_name}.png"
    bpy.context.scene.render.filepath = str(out_path)
    bpy.ops.render.render(write_still=True)
    return out_path


def compose_tiles(tile_paths, out_path: Path):
    final_width = TILE_RESOLUTION * len(tile_paths)
    final_height = TILE_RESOLUTION - TILE_CROP_BOTTOM
    canvas = [0.0] * (final_width * final_height * 4)

    for index, tile_path in enumerate(tile_paths):
        image = bpy.data.images.load(str(tile_path))
        pixels = list(image.pixels)
        dst_x0 = index * TILE_RESOLUTION

        for y in range(final_height):
            src_y = y + TILE_CROP_BOTTOM
            src_start = src_y * TILE_RESOLUTION * 4
            src_end = src_start + TILE_RESOLUTION * 4
            dst_start = (y * final_width + dst_x0) * 4
            canvas[dst_start:dst_start + TILE_RESOLUTION * 4] = pixels[src_start:src_end]

        bpy.data.images.remove(image)

    composed = bpy.data.images.new(out_path.stem, final_width, final_height, alpha=True)
    composed.pixels[:] = canvas
    out_path.parent.mkdir(parents=True, exist_ok=True)
    composed.save_render(str(out_path))
    bpy.data.images.remove(composed)


def glb_files():
    return [
        path for path in sorted(SCRIPT_DIR.rglob("*.glb"))
        if "raw" not in path.relative_to(SCRIPT_DIR).parts
        and "event" not in path.relative_to(SCRIPT_DIR).parts
    ]


def render_one(glb_path: Path):
    clear_scene()
    configure_render()
    configure_lighting()

    bpy.ops.import_scene.gltf(filepath=str(glb_path))
    meshes = mesh_objects()
    if not meshes:
        raise RuntimeError(f"No mesh objects imported from {glb_path}")

    min_pt, max_pt = center_model(meshes)
    camera, target, max_dim = create_camera(min_pt, max_pt)

    rel = glb_path.relative_to(SCRIPT_DIR).with_suffix(".png")
    out_path = OUT_DIR / rel
    tile_dir = TMP_DIR / rel.with_suffix("")
    tile_dir.mkdir(parents=True, exist_ok=True)
    tile_paths = [
        render_tile(camera, target, max_dim, view_name, tile_dir)
        for view_name, _direction in VIEW_SPECS
    ]
    compose_tiles(tile_paths, out_path)
    return rel


def main():
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)

    rendered = []
    for glb_path in glb_files():
        rel = render_one(glb_path)
        rendered.append(rel)
        print(f"RENDERED {rel}")
    shutil.rmtree(TMP_DIR)
    print(f"DONE {len(rendered)} previews -> {OUT_DIR}")


if __name__ == "__main__":
    main()
