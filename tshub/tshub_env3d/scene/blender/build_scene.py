'''
@Author: WANG Maonan
@Date: 2026-06-01 00:00:00
@Description: 静态场景构建 (Stage 2, 在 Blender 内运行).

读取 Stage 1 (scene_export.export_scene_geometry) 导出的 JSON, 在 Blender 中以
示意风格 (低饱和纯色) 构建并分文件导出 glb (Y-up, 与渲染器坐标约定一致):
- map.glb       路面 (深灰) + 路缘硬质铺装带 apron (中灰)
- ground.glb    远处绿地 (低饱和绿, 略低于路面)
- road_lines.glb / lane_lines.glb  道路边线 / 车道线 (抬高的实体条带 mesh)
- buildings.glb (仅 env 模式) 建筑轮廓挤出的浅灰灰模
- props.glb     路边小物件 (路灯、长椅等)

用法 (在 tshub 仓库根目录):
    /home/wmn/blender/blender --background --python \
        tshub/tshub_env3d/scene/blender/build_scene.py -- \
        scene.json out_dir [--assets asset_dir]

建筑走哪条路由 scene.json 自己决定 (不需要额外开关): 带 poly 生成的 json 里有真实
轮廓 -> 按轮廓挤出灰模; 不带 poly 的 json 里没有 -> 用 scatter 的位姿实例化建筑模型.
@LastEditTime: 2026-07-10
'''
import bpy
import os
import sys
import json
import math
import random
import bmesh
import mathutils
from pathlib import Path

DEFAULT_ASSET_DIR = Path(__file__).resolve().parents[2] / "_assets_3d" / "environment"

CITY_BUILDER_STYLE = {
    # Readable from top-down cameras, less debug-like than saturated primary
    # colors, and still simple enough for Panda3D realtime use.
    "materials": {
        "road":     {"name": "AsphaltWarm", "color": (0.17, 0.17, 0.16), "roughness": 0.96},
        "apron":    {"name": "ConcreteApron", "color": (0.30, 0.31, 0.29), "roughness": 0.94},
        "ground":   {"name": "MutedGrass", "color": (0.23, 0.32, 0.14), "roughness": 1.00},
        "building": {"name": "SoftConcrete", "color": (0.50, 0.52, 0.51), "roughness": 0.92},
        "lane":     {"name": "LaneMarkingWarm", "color": (0.78, 0.76, 0.70), "roughness": 0.70},
        "edge":     {"name": "EdgeMarkingOchre", "color": (0.75, 0.55, 0.16), "roughness": 0.72},
        "turn":     {"name": "TurnArrowWarm", "color": (0.86, 0.84, 0.76), "roughness": 0.68},
    },
    "z": {"ground": -0.05, "apron": -0.03, "road": 0.0, "marking": 0.02, "turn": 0.03},
    "line": {"lane_width": 0.20, "edge_width": 0.25, "turn_width": 0.24, "dash": (3.0, 3.0)},
}


# --------------- 参数解析 (-- 之后的部分) --------------- #
def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    asset_dir = str(DEFAULT_ASSET_DIR)
    pos = []
    i = 0
    while i < len(argv):
        if argv[i] in ('--assets', '--asset-dir'):
            asset_dir = argv[i + 1]; i += 2
        else:
            pos.append(argv[i]); i += 1
    if len(pos) < 2:
        raise SystemExit("usage: ... -- scene.json out_dir [--assets asset_dir]")
    return pos[0], pos[1], asset_dir


# --------------- Blender 工具 --------------- #
def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def make_material(name, color, metallic=0.0, roughness=0.9):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


def make_style_materials(style):
    return {
        key: make_material(spec["name"], spec["color"], roughness=spec["roughness"])
        for key, spec in style["materials"].items()
    }


def add_ground(bbox, material, z=-0.05):
    """远处绿地平面 (略低于路面)."""
    xmin, ymin, xmax, ymax = bbox
    verts = [(xmin, ymin, z), (xmax, ymin, z), (xmax, ymax, z), (xmin, ymax, z)]
    mesh = bpy.data.meshes.new("ground")
    obj = bpy.data.objects.new("ground", mesh)
    bpy.context.collection.objects.link(obj)
    mesh.from_pydata(verts, [], [(0, 1, 2, 3)])
    mesh.update()
    obj.data.materials.append(material)
    return obj


def add_mesh(name, verts, faces, material):
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj.data.materials.append(material)
    return obj


def ribbon_mesh(polyline, width, z, dash=None):
    """沿折线生成略抬高的条带 (实体三角网格), 用作车道线/边线.

    dash=None -> 实线 (不同方向/边线);
    dash=(dash_len, gap_len) -> 虚线 (同向车道之间), 按弧长切分.
    """
    verts, faces = [], []
    half = width / 2.0

    def emit(x0, y0, x1, y1):
        dx, dy = x1 - x0, y1 - y0
        length = math.hypot(dx, dy)
        if length < 1e-9:
            return
        nx, ny = -dy / length * half, dx / length * half
        b = len(verts)
        verts.extend([(x0 + nx, y0 + ny, z), (x0 - nx, y0 - ny, z),
                      (x1 - nx, y1 - ny, z), (x1 + nx, y1 + ny, z)])
        faces.append((b, b + 1, b + 2, b + 3))

    if dash is None: # 实线
        for i in range(len(polyline) - 1):
            emit(polyline[i][0], polyline[i][1], polyline[i + 1][0], polyline[i + 1][1])
        return verts, faces

    # 虚线: 沿弧长按 (dash_len, gap_len) 周期切分, 只在 dash 段生成条带
    dash_len, gap_len = dash
    period = dash_len + gap_len
    step = 0.5 # 采样步长 (m)
    s = 0.0
    for i in range(len(polyline) - 1):
        x0, y0 = polyline[i]; x1, y1 = polyline[i + 1]
        seg = math.hypot(x1 - x0, y1 - y0)
        if seg < 1e-9:
            continue
        n = max(1, int(seg / step))
        for k in range(n):
            t0, t1 = k / n, (k + 1) / n
            mid = s + seg * (t0 + t1) / 2.0
            if (mid % period) < dash_len: # 处于 dash 段
                emit(x0 + (x1 - x0) * t0, y0 + (y1 - y0) * t0,
                     x0 + (x1 - x0) * t1, y0 + (y1 - y0) * t1)
        s += seg
    return verts, faces


def _transform_arrow_points(points, center, heading, z):
    """Transform local arrow coordinates (x=left, y=forward) into world XY."""
    cx, cy = center
    fx, fy = math.cos(heading), math.sin(heading)
    lx, ly = -fy, fx
    return [
        (cx + px * lx + py * fx, cy + px * ly + py * fy, z)
        for px, py in points
    ]


def _arrow_head(tip, direction, length=0.62, width=0.72):
    dx, dy = direction
    mag = math.hypot(dx, dy)
    if mag < 1e-6:
        return []
    dx, dy = dx / mag, dy / mag
    px, py = -dy, dx
    base_x, base_y = tip[0] - dx * length, tip[1] - dy * length
    half = width / 2.0
    return [
        tip,
        (base_x + px * half, base_y + py * half),
        (base_x - px * half, base_y - py * half),
    ]


def _turn_arrow_components(turns):
    """Return local arrow strokes and heads for one lane marking.

    Local x points to the lane's left side, local y points forward.
    """
    turns = list(dict.fromkeys(turns))
    if not turns:
        return [], []

    paths = [[(0.0, -2.15), (0.0, 0.15)]]
    heads = []

    if "straight" in turns:
        paths.append([(0.0, 0.05), (0.0, 0.95)])
        heads.append(((0.0, 1.65), (0.0, 1.0)))
    if "left" in turns:
        paths.append([(0.0, 0.05), (0.24, 0.48), (0.72, 0.48)])
        heads.append(((1.24, 0.48), (1.0, 0.0)))
    if "right" in turns:
        paths.append([(0.0, 0.05), (-0.24, 0.48), (-0.72, 0.48)])
        heads.append(((-1.24, 0.48), (-1.0, 0.0)))
    if "uturn" in turns:
        paths.append([(0.0, 0.05), (0.0, 0.78), (0.48, 0.98), (0.90, 0.56), (0.90, -0.12)])
        heads.append(((0.90, -0.72), (0.0, -1.0)))

    return paths, heads


def turn_arrow_mesh(marking, width, z):
    """Build a flat lane-turn arrow marking from a JSON turn_markings record."""
    turns = marking.get("turns") or str(marking.get("turn", "")).split("+")
    paths, heads = _turn_arrow_components([turn for turn in turns if turn])
    if not paths:
        return [], []

    center = marking["center"]
    heading = marking["heading"]
    verts, faces = [], []
    for path in paths:
        world_path = [(x, y) for x, y, _ in _transform_arrow_points(path, center, heading, z)]
        v, f = ribbon_mesh(world_path, width=width, z=z)
        b = len(verts)
        verts.extend(v)
        faces.extend(tuple(i + b for i in face) for face in f)

    for head_tip, head_dir in heads:
        head = _arrow_head(head_tip, head_dir)
        if not head:
            continue
        b = len(verts)
        verts.extend(_transform_arrow_points(head, center, heading, z))
        faces.append((b, b + 1, b + 2))
    return verts, faces


# --------------- OSM 建筑挤出 (真实轮廓灰模, city-builder 多色) --------------- #
# 有 OSM footprint 时按真实轮廓挤出棱柱 (尺寸正确, 且成千上万栋也很小),
# 而不是摆放固定大小的精细模型 (大小对不上). 无 OSM 时才用精细模型 (见 build).
BUILDING_MASSING_COLORS = [
    (0.62, 0.56, 0.47),  # tan
    (0.55, 0.58, 0.60),  # cool grey
    (0.60, 0.45, 0.38),  # terracotta
    (0.48, 0.53, 0.47),  # sage
    (0.66, 0.62, 0.54),  # sand
    (0.50, 0.47, 0.45),  # warm grey
    (0.52, 0.50, 0.58),  # slate lavender
    (0.44, 0.52, 0.56),  # blue-grey
]


def _ensure_ccw(footprint):
    """规整为逆时针 (CCW), 保证挤出后墙面/屋顶法线朝外 (否则渲染成黑面)."""
    area = 0.0
    n = len(footprint)
    for i in range(n):
        x0, y0 = footprint[i]
        x1, y1 = footprint[(i + 1) % n]
        area += x0 * y1 - x1 * y0
    return footprint if area >= 0 else footprint[::-1]


def _prism_faces(footprint, height):
    """挤出 footprint -> (verts, 墙+底面, 顶面). 底面封口 -> 闭合流形, 便于重算法线."""
    fp = [(float(x), float(y)) for x, y in footprint]
    if len(fp) >= 2 and fp[0] == fp[-1]:  # OSM 轮廓常闭合, 去掉重复末点
        fp = fp[:-1]
    if len(fp) < 3:
        return [], [], []
    fp = _ensure_ccw(fp)
    n = len(fp)
    verts = [(x, y, 0.0) for x, y in fp] + [(x, y, float(height)) for x, y in fp]
    walls = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    bottom = [tuple(range(n))]                  # 底面 (封口, 看不到)
    roof = [tuple(range(n, 2 * n))]             # 顶面 (n 边形, 导出时三角化)
    return verts, walls + bottom, roof


def _add_massing(name, verts, side_faces, roof, wall_mat, roof_mat):
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    mesh.from_pydata(verts, [], side_faces + roof)
    mesh.update()
    # 挤出体是闭合流形, 重算法线使全部朝外 (修复轮廓凹/自交导致的黑面).
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    obj.data.materials.append(wall_mat)  # index 0 = 墙面/底面
    obj.data.materials.append(roof_mat)  # index 1 = 屋顶
    roof_start = len(side_faces)
    for idx, poly in enumerate(mesh.polygons):
        poly.material_index = 1 if idx >= roof_start else 0
    return obj


def extrude_buildings(buildings, seed=0):
    """按 OSM footprint 挤出建筑灰模 (正确尺寸 + 真实层高 + 多色, 共享材质)."""
    rng = random.Random(seed)
    wall_mats = [make_material(f"massing_wall_{i}", c, roughness=0.92)
                 for i, c in enumerate(BUILDING_MASSING_COLORS)]
    roof_mats = [make_material(f"massing_roof_{i}", tuple(v * 0.72 for v in c), roughness=0.90)
                 for i, c in enumerate(BUILDING_MASSING_COLORS)]
    objs = []
    for idx, b in enumerate(buildings):
        verts, side_faces, roof = _prism_faces(b['footprint'], b.get('height') or 9.0)
        if not verts:
            continue
        ci = rng.randrange(len(BUILDING_MASSING_COLORS))
        objs.append(_add_massing(f"building_{idx}", verts, side_faces, roof,
                                 wall_mats[ci], roof_mats[ci]))
    return objs


def _asset_files(asset_dir, category):
    root = Path(asset_dir) / category
    if not root.exists():
        return []
    return sorted(str(path) for path in root.glob("*.glb"))


def _bounds(objects):
    mins = [1e18, 1e18, 1e18]
    maxs = [-1e18, -1e18, -1e18]
    for obj in objects:
        for corner in obj.bound_box:
            v = obj.matrix_world @ mathutils.Vector(corner)
            for i in range(3):
                mins[i] = min(mins[i], v[i])
                maxs[i] = max(maxs[i], v[i])
    return mins, maxs


# --------------- 资产实例化 (共享 mesh, 保持 glb 小) --------------- #
# 每种资产只导入一次作为模板 mesh, 所有实例共享同一 mesh 数据 (仅节点 TRS 不同).
# 导出的 glb 中几何只存一份 -> 沿街密集摆放也不会让文件变大 (避免素材复制).
ASSET_LIMITS = {"buildings": 8, "trees": 8, "props": 12}


def _spread(files, limit):
    """跨排序列表均匀取样 (而非取前 N 个), 使建筑高矮/树种都有变化."""
    if len(files) <= limit:
        return files
    step = len(files) / limit
    return [files[int(i * step)] for i in range(limit)]


def _load_templates(asset_dir, category):
    """导入至多若干不同资产各一次, 烘焙为竖直模板 (底部 z=0), 返回其 mesh + 尺寸."""
    templates = []
    for filepath in _spread(_asset_files(asset_dir, category), ASSET_LIMITS.get(category, 8)):
        before = set(bpy.context.scene.objects)
        bpy.ops.import_scene.gltf(filepath=filepath)
        new = [o for o in bpy.context.scene.objects if o not in before]
        meshes = [o for o in new if o.type == 'MESH']
        extras = [o for o in new if o.type != 'MESH']  # empties/armatures, not exported
        if not meshes:
            for o in extras:
                bpy.data.objects.remove(o, do_unlink=True)
            continue
        obj = meshes[0]
        if len(meshes) > 1:  # join merges meshes[1:] into obj (they become stale)
            bpy.ops.object.select_all(action='DESELECT')
            for m in meshes:
                m.select_set(True)
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.join()
        # 烘焙导入矩阵 -> mesh 局部坐标即竖直, 实例只需干净的 TRS
        obj.data.transform(obj.matrix_world)
        obj.matrix_world = mathutils.Matrix.Identity(4)
        mins, maxs = _bounds([obj])
        mesh = obj.data
        templates.append({'name': Path(filepath).stem,
                          'mesh': mesh,
                          'size': (maxs[0] - mins[0], maxs[1] - mins[1], maxs[2] - mins[2])})
        # 移除模板对象本身 (不导出); 其 mesh 数据由后续实例引用而保留
        bpy.data.objects.remove(obj, do_unlink=True)
        for o in extras:
            bpy.data.objects.remove(o, do_unlink=True)
    return templates


def _instance(mesh, name, x, y, yaw, scale):
    """共享 mesh 的一个实例, 仅设置节点 TRS (不烘焙几何)."""
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.location = (float(x), float(y), 0.0)
    obj.rotation_euler = (0.0, 0.0, float(yaw))
    obj.scale = (scale, scale, scale)
    return obj


def instance_props(templates, placements, prefix, size_fit=False):
    """沿给定位姿实例化模板 (循环使用有限模板集).

    size_fit=True 时 (建筑), 按 OSM footprint 的短边等比缩放, 避免窗户变形.
    """
    objs = []
    if not templates:
        return objs
    by_name = {tmpl.get('name'): tmpl for tmpl in templates}
    for idx, place in enumerate(placements):
        tmpl = by_name.get(place.get('asset')) or templates[idx % len(templates)]
        scale = float(place.get('scale', 1.0))
        if size_fit and place.get('size'):
            native_min = max(min(tmpl['size'][0], tmpl['size'][1]), 1e-3)
            target_min = max(min(place['size'][0], place['size'][1]), 1e-3)
            scale = min(max(target_min / native_min, 0.6), 2.5)
        objs.append(_instance(tmpl['mesh'], f"{prefix}_{idx}",
                              place['pos'][0], place['pos'][1], place.get('yaw', 0.0), scale))
    return objs


def export_group(objs, path):
    """仅导出指定对象到一个 glb (沿用旧接口的分文件存储)."""
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True)


# --------------- 构建 --------------- #
def build(scene_json, out_dir, asset_dir=None):
    data = json.loads(open(scene_json).read())
    os.makedirs(out_dir, exist_ok=True)
    clear_scene()
    asset_dir = asset_dir or str(DEFAULT_ASSET_DIR)

    materials = make_style_materials(CITY_BUILDER_STYLE)
    z = CITY_BUILDER_STYLE["z"]
    line_style = CITY_BUILDER_STYLE["line"]

    # 1. 远处绿地 (包围盒平面, 最低)
    ground_objs = [add_ground(data['bbox'], materials["ground"], z=z["ground"])]

    # 2. 路面 (深灰, z=0) + 路缘灰色铺装带 (中灰, z=-0.03, 贴着道路向外扩)
    road_objs = []
    for idx, road in enumerate(data['roads']):
        verts = [(x, y, z["road"]) for x, y in road['vertices']]
        road_objs.append(add_mesh(f"road_{idx}", verts, [tuple(f) for f in road['faces']], materials["road"]))
    for idx, ap in enumerate(data.get('apron', [])):
        verts = [(x, y, z["apron"]) for x, y in ap['vertices']]
        road_objs.append(add_mesh(f"apron_{idx}", verts, [tuple(f) for f in ap['faces']], materials["apron"]))

    # 3. 车道线 / 边线 (抬高的实体条带, 所有渲染器可见)
    #    同向车道之间 -> 虚线; 不同方向 / 道路边线 -> 实线
    lane_objs = []
    for idx, line in enumerate(data['lane_dividers']):
        v, f = ribbon_mesh(
            line,
            width=line_style["lane_width"],
            z=z["marking"],
            dash=line_style["dash"],
        )
        if v:
            lane_objs.append(add_mesh(f"lane_{idx}", v, f, materials["lane"]))
    for idx, marking in enumerate(data.get('turn_markings', [])):
        v, f = turn_arrow_mesh(
            marking,
            width=line_style["turn_width"],
            z=z["turn"],
        )
        if v:
            lane_objs.append(add_mesh(f"turn_{idx}_{marking.get('turn', 'unknown')}", v, f, materials["turn"]))
    edge_objs = []
    for idx, line in enumerate(data['edge_borders']):
        v, f = ribbon_mesh(line, width=line_style["edge_width"], z=z["marking"])
        if v:
            edge_objs.append(add_mesh(f"edge_{idx}", v, f, materials["edge"]))

    # 4. 城市道具: 沿路树木 / 建筑 / 小物件.
    #    位姿由 Stage 1 (scene_data/scatter.py, shapely) 计算; 这里只按位姿实例化共享模板.
    scatter = data.get('scatter', {})
    tree_templates = _load_templates(asset_dir, "trees")
    prop_templates = _load_templates(asset_dir, "props")

    vegetation_objs = instance_props(tree_templates, scatter.get('trees', []), "tree")
    prop_objs = instance_props(prop_templates, scatter.get('props', []), "prop")

    if data.get('buildings'):  # 有 OSM: 按真实轮廓挤出灰模 (尺寸正确)
        building_objs = extrude_buildings(data['buildings'])
    else:  # 无 OSM: 沿街摆放精细建筑模型 (装饰用)
        building_templates = _load_templates(asset_dir, "buildings")
        building_objs = instance_props(building_templates, scatter.get('buildings', []),
                                       "building", size_fit=True)

    # 5. 分文件导出 (沿用旧接口文件名; 路面+路缘 -> map.glb)
    export_group(road_objs, os.path.join(out_dir, "map.glb"))
    export_group(ground_objs, os.path.join(out_dir, "ground.glb"))
    export_group(edge_objs, os.path.join(out_dir, "road_lines.glb"))
    export_group(lane_objs, os.path.join(out_dir, "lane_lines.glb"))
    for objs, fname in ((building_objs, "buildings.glb"),
                        (vegetation_objs, "vegetation.glb"),
                        (prop_objs, "props.glb")):
        path = os.path.join(out_dir, fname)
        if objs:
            export_group(objs, path)
        elif os.path.exists(path):
            os.remove(path)
    print(f"BUILD_DONE: {out_dir} (style=city_builder, roads={len(data['roads'])}, "
          f"apron={len(data.get('apron', []))}, lanes={len(lane_objs)}, "
          f"turns={len(data.get('turn_markings', []))}, edges={len(edge_objs)}, "
          f"buildings={len(building_objs)}, vegetation={len(vegetation_objs)}, "
          f"props={len(prop_objs)}, assets={asset_dir})")


if __name__ == '__main__':
    scene_json, out_dir, asset_dir = parse_args()
    build(scene_json, out_dir, asset_dir)
