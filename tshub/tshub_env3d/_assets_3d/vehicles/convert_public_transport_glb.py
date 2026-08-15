'''
@Author: WANG Maonan
@Date: 2026-07-11
@Description: Rebuild selected vehicle GLBs from raw assets.

Run with Blender from the repository root:
    /home/wmn/blender/blender --background --python \
        tshub/tshub_env3d/_assets_3d/vehicles/convert_public_transport_glb.py

The Blender import/export path is used only for geometry orientation, scale and
origin.  After export, the raw GLB material/texture/image payload is copied back
into the converted GLB by material name so texture pixels are not reprocessed by
Blender.
'''
import json
import math
import os
import re
import struct
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


SCRIPT_DIR = Path(__file__).resolve().parent
PUBLIC_DIR = SCRIPT_DIR / "public_transport"
BACKGROUND_DIR = SCRIPT_DIR / "background"
RAW_DIR = PUBLIC_DIR / "raw"


SPECS = {
    "emergency": {
        "raw": RAW_DIR / "shvan_92_ambulance_-_low_poly_model.glb",
        "out": PUBLIC_DIR / "emergency.glb",
        "rotation_z_deg": 90.0,
        "target_dims": (2.574, 5.500, 2.479),
        "scale_mode": "uniform_y",
        "target_min_z": 0.0,
        "material_overrides": {
            "UCB_BOTTOM": {"metallicFactor": 0.0, "roughnessFactor": 0.75},
            "UCB_Lights_and_Glass_Transperent": {"metallicFactor": 0.0, "roughnessFactor": 0.28},
            "UCB_Interiors_1": {"metallicFactor": 0.0, "roughnessFactor": 0.8},
            "Shvan92_bodymat": {"metallicFactor": 0.0, "roughnessFactor": 0.72},
            "UCB_Lights_and_Glass": {"metallicFactor": 0.0, "roughnessFactor": 0.35},
            "RB1c_Tire_1k": {"metallicFactor": 0.0, "roughnessFactor": 0.78},
            "Numberplates_Misk_U": {"metallicFactor": 0.0, "roughnessFactor": 0.55},
            "Carbadges_misc_U": {"metallicFactor": 0.15, "roughnessFactor": 0.45},
        },
    },
    "fire_engine": {
        "raw": RAW_DIR / "fire_truck.glb",
        "out": PUBLIC_DIR / "fire_engine.glb",
        "rotation_z_deg": 180.0,
        "target_dims": (2.818, 8.000, 3.861),
        "scale_mode": "uniform_y",
        "target_min_z": 0.0,
        "material_overrides": {
            "carpaint_second": {"metallicFactor": 0.05, "roughnessFactor": 0.6},
            "black": {"metallicFactor": 0.0, "roughnessFactor": 0.65},
            "chrome": {"metallicFactor": 0.55, "roughnessFactor": 0.28},
            "mattemetal": {"metallicFactor": 0.35, "roughnessFactor": 0.45},
            "redglass": {"metallicFactor": 0.0, "roughnessFactor": 0.25},
            "clearglass": {"metallicFactor": 0.0, "roughnessFactor": 0.25},
            "interior": {"metallicFactor": 0.0, "roughnessFactor": 0.72},
            "windowglass": {"metallicFactor": 0.0, "roughnessFactor": 0.3},
            "orangeglass": {"metallicFactor": 0.0, "roughnessFactor": 0.25},
            "carpaint": {"metallicFactor": 0.05, "roughnessFactor": 0.62},
            "material": {"metallicFactor": 0.1, "roughnessFactor": 0.55},
            "blueglass": {"metallicFactor": 0.0, "roughnessFactor": 0.28},
            "white": {"metallicFactor": 0.0, "roughnessFactor": 0.65},
            "yellow": {"metallicFactor": 0.0, "roughnessFactor": 0.55},
        },
    },
    "police": {
        "raw": RAW_DIR / "police_car_city.glb",
        "out": PUBLIC_DIR / "police.glb",
        "rotation_z_deg": 180.0,
        "target_dims": (1.902, 4.400, 1.550),
        "scale_mode": "xyz",
        "target_min_z": 0.0,
        "material_overrides": {
            "mat_0-chassis_gen1.jpg": {"metallicFactor": 0.05, "roughnessFactor": 0.65},
            "mat_1-color_0.000000-0.000000-0.000000.jpg": {"metallicFactor": 0.0, "roughnessFactor": 0.55},
            "mat_2-us_police_car_bo1.jpg": {"metallicFactor": 0.05, "roughnessFactor": 0.65},
            "mat_3-plates_us1.jpg": {"metallicFactor": 0.0, "roughnessFactor": 0.5},
            "mat_4-saloon_wheel1.jpg": {"metallicFactor": 0.0, "roughnessFactor": 0.7},
            "mat_5-color_1.000000-1.000000-1.000000.jpg": {"metallicFactor": 0.0, "roughnessFactor": 0.65},
        },
    },
    "taxi": {
        "raw": RAW_DIR / "2001_crown_victoria_taxi_game_prop.glb",
        "out": BACKGROUND_DIR / "taxi.glb",
        "rotation_z_deg": 180.0,
        "target_dims": (1.902, 4.400, 1.500),
        "scale_mode": "xyz",
        "target_min_z": 0.0,
        "material_overrides": {
            "main_frame": {"metallicFactor": 0.1, "roughnessFactor": 0.55},
            "glass": {"metallicFactor": 0.0, "roughnessFactor": 0.35},
            "glass_window": {"metallicFactor": 0.0, "roughnessFactor": 0.35},
            "interior2": {"metallicFactor": 0.0, "roughnessFactor": 0.75},
            "interior_bottom": {"metallicFactor": 0.0, "roughnessFactor": 0.75},
            "wheels_and_parts": {"metallicFactor": 0.0, "roughnessFactor": 0.65},
            "plate": {"metallicFactor": 0.0, "roughnessFactor": 0.5},
            "taxi_sign": {"metallicFactor": 0.0, "roughnessFactor": 0.5},
        },
    },
}


JSON_CHUNK = 0x4E4F534A
BIN_CHUNK = 0x004E4942
FLOAT = 5126
VEC3 = "VEC3"


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


def import_glb(path: Path):
    clear_scene()
    bpy.ops.import_scene.gltf(filepath=str(path))
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


def transform_meshes(meshes, spec):
    rot = Matrix.Rotation(math.radians(spec["rotation_z_deg"]), 4, "Z")
    for obj in meshes:
        obj.matrix_world = rot @ obj.matrix_world
    bpy.context.view_layer.update()

    min_pt, max_pt = mesh_world_bounds(meshes)
    dims = max_pt - min_pt
    target = Vector(spec["target_dims"])
    if spec["scale_mode"] == "uniform_y":
        scale_factor = target.y / dims.y
        scale_vec = Vector((scale_factor, scale_factor, scale_factor))
    elif spec["scale_mode"] == "xyz":
        scale_vec = Vector((target.x / dims.x, target.y / dims.y, target.z / dims.z))
    else:
        raise ValueError(f"Unknown scale_mode: {spec['scale_mode']}")

    scale = Matrix.Diagonal((scale_vec.x, scale_vec.y, scale_vec.z, 1.0))
    for obj in meshes:
        obj.matrix_world = scale @ obj.matrix_world
    bpy.context.view_layer.update()

    min_pt, max_pt = mesh_world_bounds(meshes)
    center = (min_pt + max_pt) * 0.5
    translate = Matrix.Translation(Vector((-center.x, -center.y, spec["target_min_z"] - min_pt.z)))
    for obj in meshes:
        obj.matrix_world = translate @ obj.matrix_world
    bpy.context.view_layer.update()


def bake_world_transforms(meshes):
    for obj in meshes:
        world = obj.matrix_world.copy()
        obj.parent = None
        obj.data = obj.data.copy()
        obj.data.transform(world)
        obj.matrix_world = Matrix.Identity(4)
    for obj in list(bpy.context.scene.objects):
        if obj.type != "MESH":
            bpy.data.objects.remove(obj, do_unlink=True)
    bpy.context.view_layer.update()


def parent_meshes_to_root(meshes, root_name: str):
    """Keep the exported GLB tidy: one root node with all mesh parts below it."""
    root = bpy.data.objects.new(root_name, None)
    bpy.context.collection.objects.link(root)
    root.empty_display_type = "CUBE"
    root.empty_display_size = 1.0
    root.matrix_world = Matrix.Identity(4)

    for obj in meshes:
        obj.parent = root
        obj.matrix_parent_inverse = root.matrix_world.inverted()
    bpy.context.view_layer.update()


def export_geometry(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=str(path),
        export_format="GLB",
        export_image_format="AUTO",
    )


def _align4(data: bytes, pad: bytes = b" ") -> bytes:
    return data + pad * ((4 - len(data) % 4) % 4)


def read_glb(path: Path):
    blob = path.read_bytes()
    if blob[:4] != b"glTF":
        raise ValueError(f"{path} is not GLB")
    version, length = struct.unpack_from("<II", blob, 4)
    if version != 2 or length != len(blob):
        raise ValueError(f"{path} has invalid GLB header")

    offset = 12
    chunks = {}
    while offset < len(blob):
        chunk_len, chunk_type = struct.unpack_from("<II", blob, offset)
        offset += 8
        chunks[chunk_type] = blob[offset:offset + chunk_len]
        offset += chunk_len
    return json.loads(chunks[JSON_CHUNK].decode("utf-8")), chunks.get(BIN_CHUNK, b"")


def write_glb(path: Path, gltf: dict, bin_chunk: bytes):
    json_bytes = _align4(json.dumps(gltf, separators=(",", ":")).encode("utf-8"), b" ")
    bin_bytes = _align4(bin_chunk, b"\x00")
    total_len = 12 + 8 + len(json_bytes) + 8 + len(bin_bytes)
    with path.open("wb") as f:
        f.write(struct.pack("<4sII", b"glTF", 2, total_len))
        f.write(struct.pack("<II", len(json_bytes), JSON_CHUNK))
        f.write(json_bytes)
        f.write(struct.pack("<II", len(bin_bytes), BIN_CHUNK))
        f.write(bin_bytes)


def _buffer_view_bytes(gltf: dict, bin_chunk: bytes, view_idx: int) -> bytes:
    view = gltf["bufferViews"][view_idx]
    start = view.get("byteOffset", 0)
    end = start + view["byteLength"]
    return bin_chunk[start:end]


def _position_accessor_indices(gltf: dict):
    seen = set()
    for mesh in gltf.get("meshes", []):
        for prim in mesh.get("primitives", []):
            idx = prim.get("attributes", {}).get("POSITION")
            if idx is not None and idx not in seen:
                seen.add(idx)
                yield idx


def _position_accessor_layout(gltf: dict, accessor_idx: int):
    accessor = gltf["accessors"][accessor_idx]
    if accessor.get("componentType") != FLOAT or accessor.get("type") != VEC3:
        raise RuntimeError(f"Unsupported POSITION accessor format: {accessor}")
    view = gltf["bufferViews"][accessor["bufferView"]]
    offset = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
    stride = view.get("byteStride", 12)
    return accessor, offset, stride


def snap_glb_min_z(path: Path, target_min_z: float):
    gltf, bin_chunk = read_glb(path)
    bin_out = bytearray(bin_chunk)
    min_z = None
    layouts = []

    for accessor_idx in _position_accessor_indices(gltf):
        accessor, offset, stride = _position_accessor_layout(gltf, accessor_idx)
        layouts.append((accessor, offset, stride))
        for i in range(accessor["count"]):
            z = struct.unpack_from("<f", bin_out, offset + i * stride + 8)[0]
            min_z = z if min_z is None else min(min_z, z)

    if min_z is None:
        raise RuntimeError(f"No POSITION accessors found in {path}")

    dz = float(target_min_z) - min_z
    if abs(dz) < 1e-6:
        return

    for accessor, offset, stride in layouts:
        for i in range(accessor["count"]):
            pos = offset + i * stride + 8
            z = struct.unpack_from("<f", bin_out, pos)[0]
            struct.pack_into("<f", bin_out, pos, z + dz)
        if "min" in accessor:
            accessor["min"][2] += dz
        if "max" in accessor:
            accessor["max"][2] += dz

    gltf["buffers"][0]["byteLength"] = len(bin_out)
    write_glb(path, gltf, bytes(bin_out))


def _base_material_name(name: str) -> str:
    return re.sub(r"\.\d{3}$", "", name or "")


def restore_raw_material_payload(converted_path: Path, raw_path: Path):
    converted, converted_bin = read_glb(converted_path)
    raw, raw_bin = read_glb(raw_path)

    raw_materials = raw.get("materials", [])
    raw_material_by_name = {mat.get("name"): idx for idx, mat in enumerate(raw_materials)}
    raw_material_by_base_name = {
        _base_material_name(mat.get("name")): idx
        for idx, mat in enumerate(raw_materials)
    }
    converted_materials = converted.get("materials", [])
    converted_to_raw = {}
    for idx, mat in enumerate(converted_materials):
        name = mat.get("name")
        if name in raw_material_by_name:
            converted_to_raw[idx] = raw_material_by_name[name]
            continue
        base_name = _base_material_name(name)
        if base_name in raw_material_by_base_name:
            converted_to_raw[idx] = raw_material_by_base_name[base_name]

    missing = [
        mat.get("name")
        for idx, mat in enumerate(converted_materials)
        if idx not in converted_to_raw
    ]
    if missing:
        raise RuntimeError(f"Materials missing in raw asset {raw_path.name}: {missing}")

    for mesh in converted.get("meshes", []):
        for prim in mesh.get("primitives", []):
            if "material" in prim:
                prim["material"] = converted_to_raw[prim["material"]]

    converted["materials"] = json.loads(json.dumps(raw_materials))
    converted["textures"] = json.loads(json.dumps(raw.get("textures", [])))
    converted["samplers"] = json.loads(json.dumps(raw.get("samplers", [])))

    converted.setdefault("bufferViews", [])
    converted.setdefault("buffers", [{"byteLength": len(converted_bin)}])
    new_images = []
    bin_out = _align4(converted_bin, b"\x00")
    for image in raw.get("images", []):
        image = json.loads(json.dumps(image))
        if "bufferView" in image:
            image_bytes = _buffer_view_bytes(raw, raw_bin, image["bufferView"])
            bin_out = _align4(bin_out, b"\x00")
            image["bufferView"] = len(converted["bufferViews"])
            converted["bufferViews"].append(
                {
                    "buffer": 0,
                    "byteOffset": len(bin_out),
                    "byteLength": len(image_bytes),
                }
            )
            bin_out += image_bytes
        new_images.append(image)

    converted["images"] = new_images
    converted["buffers"][0]["byteLength"] = len(bin_out)
    write_glb(converted_path, converted, bin_out)


def apply_material_overrides(path: Path, overrides: dict):
    if not overrides:
        return

    gltf, bin_chunk = read_glb(path)
    for material in gltf.get("materials", []):
        material_name = _base_material_name(material.get("name"))
        if material_name not in overrides:
            continue
        pbr = material.setdefault("pbrMetallicRoughness", {})
        for key, value in overrides[material_name].items():
            pbr[key] = value
    write_glb(path, gltf, bin_chunk)


def convert_one(name: str, spec: dict):
    print(f"CONVERT {name}: {spec['raw']} -> {spec['out']}")
    meshes = import_glb(spec["raw"])
    transform_meshes(meshes, spec)
    bake_world_transforms(meshes)
    parent_meshes_to_root(meshes, f"{name}_vehicle")
    tmp_out = spec["out"].with_suffix(".tmp.glb")
    export_geometry(tmp_out)
    restore_raw_material_payload(tmp_out, spec["raw"])
    apply_material_overrides(tmp_out, spec.get("material_overrides"))
    os.replace(tmp_out, spec["out"])

    meshes = import_glb(spec["out"])
    min_pt, max_pt = mesh_world_bounds(meshes)
    dims = max_pt - min_pt
    print(
        f"DONE {name}: dims=({dims.x:.3f}, {dims.y:.3f}, {dims.z:.3f}) "
        f"min=({min_pt.x:.3f}, {min_pt.y:.3f}, {min_pt.z:.3f})"
    )


def main():
    for name, spec in SPECS.items():
        convert_one(name, spec)


if __name__ == "__main__":
    main()
