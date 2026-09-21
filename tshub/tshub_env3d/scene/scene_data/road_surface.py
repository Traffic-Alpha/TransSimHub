'''
@Author: WANG Maonan
@Date: 2026-08-18
@Description: 路面几何 -> 纯数据 (两种输入模式共用).

把 SumoNet3D 给出的道路多边形三角化成 Blender 能直接建 mesh 的 vertices/faces,
并顺带算出路缘硬质铺装带 (apron): 道路 union 向外扩 apron_width 再简化。
'''
from shapely import constrained_delaunay_triangles
from shapely.ops import unary_union
from typing import List


def _triangulate_polygon(polygon):
    """多边形 (可含洞) -> 三角形列表.

    用**约束** Delaunay: 三角化严格贴合多边形的边界与洞, 凹多边形也精确 ——
    apron 是整个路网 union 外扩出来的大凹多边形, 必须如此
    (无约束 Delaunay 会把凹处填平、又丢掉贴边的三角形).
    SUMO 的路面多边形在急转弯处偶尔自相交, 而约束 Delaunay 只吃合法输入,
    所以先 buffer(0) 洗一遍.
    """
    if not polygon.is_valid:
        polygon = polygon.buffer(0)
    return [tri for tri in constrained_delaunay_triangles(polygon).geoms if not tri.is_empty]


def polygon_to_mesh(poly, precision: int = 4):
    """Convert a shapely polygon, including holes, to JSON-safe vertices/faces."""
    verts: List[list] = []
    faces: List[list] = []
    index = {}
    for tri in _triangulate_polygon(poly):
        face = []
        for x, y in list(tri.exterior.coords)[:3]:
            key = (round(float(x), precision), round(float(y), precision))
            if key not in index:
                index[key] = len(verts)
                verts.append([float(x), float(y)])
            face.append(index[key])
        if len(set(face)) == 3:
            faces.append(face)
    return verts, faces


def polylines_to_json(lines):
    """Convert line point tuples from sumolib into JSON-safe lists."""
    return [[[float(p[0]), float(p[1])] for p in line] for line in lines]


def build_road_meshes(road_polys, apron_width: float = 5.0):
    """道路多边形 -> (路面 mesh 列表, 路缘铺装带 mesh 列表).

    apron 是贴着道路向外扩的一圈灰色硬质铺装, 让路面和绿地之间有过渡;
    SUMO 的道路多边形偶尔自相交, 所以先 buffer(0) 清洗再 union。
    """
    roads = []
    for poly, _metadata in road_polys:
        verts, faces = polygon_to_mesh(poly)
        if verts and faces:
            roads.append({'vertices': verts, 'faces': faces})

    apron = []
    try:
        road_union = unary_union([p.buffer(0) for p, _ in road_polys])
        verts, faces = polygon_to_mesh(road_union.buffer(apron_width).simplify(0.3))
        if verts and faces:
            apron.append({'vertices': verts, 'faces': faces})
    except Exception as exc:
        print(f"WARN: apron generation failed, skipped ({exc})")

    return roads, apron
